from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import subprocess
import os
import time
import threading


# ============================================================
# Configuration
# ============================================================

app = FastAPI()

MOD_DIR = Path("/home/opc/minecraft/server2/mods")

CONTAINER = "minecraft2"

RCON_HOST = "127.0.0.1"
RCON_PORT = "25576"
RCON_PASS = os.environ.get("MCRCON_PASS")

MAX_UPLOAD_SIZE = 500 * 1024 * 1024

STOP_TIMEOUT = 120
FORGE_READY_TIMEOUT = 300

FORGE_READY_TEXT = 'For help, type "help"'

MOD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Restart State
# ============================================================

restart_lock = threading.Lock()

restart_state = {
    "in_progress": False,
    "phase": None,
    "message": "",
    "error": None,
}


def set_restart_state(
    *,
    in_progress=None,
    phase=None,
    message=None,
    error=None
):
    """
    Update restart state safely.
    """

    with restart_lock:

        if in_progress is not None:
            restart_state["in_progress"] = in_progress

        if phase is not None:
            restart_state["phase"] = phase

        if message is not None:
            restart_state["message"] = message

        restart_state["error"] = error


def get_restart_state():
    """
    Return a copy of restart state.
    """

    with restart_lock:
        return dict(restart_state)


# ============================================================
# Podman Helpers
# ============================================================

def podman(*args, timeout=30):
    """
    Execute Podman command.
    """

    result = subprocess.run(
        ["podman", *args],
        capture_output=True,
        text=True,
        timeout=timeout
    )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Podman command failed"
        )

    return result.stdout.strip()


def get_container_status():
    """
    Return container status.
    """

    try:

        return podman(
            "inspect",
            "-f",
            "{{.State.Status}}",
            CONTAINER
        )

    except Exception:

        return "unknown"


def get_container_logs(tail=300):
    """
    Read recent container logs.

    stdout/stderr are combined because Podman may emit
    container logs on either stream.
    """

    result = subprocess.run(
        [
            "podman",
            "logs",
            "--tail",
            str(tail),
            CONTAINER
        ],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:

        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Unable to read container logs"
        )

    return (
        (result.stdout or "")
        +
        (result.stderr or "")
    )


# ============================================================
# Forge Ready Detection
# ============================================================

def get_current_run_logs():
    """
    Return logs for the current container run.

    Important:

    We intentionally do NOT use:

        podman inspect .State.StartedAt
        podman logs --since <StartedAt>

    because the timestamp format returned by Podman can vary.

    Instead, the restart worker records the current log line
    count immediately after podman start and uses that as the
    beginning of the new startup log.

    Outside a Web restart, Ready detection falls back to
    recent logs.
    """

    return get_container_logs(1000)


def is_forge_ready():
    """
    Determine whether Forge appears Ready.

    During an active restart, the restart worker is the
    authoritative source of state.

    Outside restart processing, recent logs are checked.
    """

    status = get_container_status()

    if status != "running":
        return False

    state = get_restart_state()

    if state["in_progress"]:

        return state["phase"] == "ready"

    try:

        logs = get_current_run_logs()

        return FORGE_READY_TEXT in logs

    except Exception:

        return False


# ============================================================
# RCON
# ============================================================

def send_rcon(command: str):
    """
    Send Minecraft command through RCON.
    """

    if not RCON_PASS:

        raise RuntimeError(
            "MCRCON_PASS is not configured"
        )

    return subprocess.run(
        [
            "mcrcon",
            "-H",
            RCON_HOST,
            "-P",
            RCON_PORT,
            "-p",
            RCON_PASS,
            command
        ],
        capture_output=True,
        text=True,
        timeout=15
    )


# ============================================================
# Restart Helpers
# ============================================================

def wait_for_clean_stop():
    """
    Wait for Minecraft container to exit cleanly.
    """

    deadline = time.time() + STOP_TIMEOUT

    while time.time() < deadline:

        status = get_container_status()

        if status in (
            "exited",
            "stopped"
        ):
            return True

        time.sleep(2)

    return False


def wait_for_container_running():
    """
    Wait briefly for Podman container to enter running state.
    """

    deadline = time.time() + 30

    while time.time() < deadline:

        if get_container_status() == "running":
            return True

        time.sleep(1)

    return False


def wait_for_forge_ready():
    """
    Wait for the NEW Forge startup to reach Done.

    The log baseline is captured immediately after the
    container has started.

    Only log content appearing after that baseline is used
    for Ready detection.
    """

    if not wait_for_container_running():
        return False, "Container did not enter running state"

    # Allow logging subsystem to settle.
    time.sleep(1)

    try:
        baseline_logs = get_container_logs(10000)
    except Exception:
        baseline_logs = ""

    baseline_length = len(baseline_logs)

    deadline = time.time() + FORGE_READY_TIMEOUT
    latest_new_logs = ""

    while time.time() < deadline:

        status = get_container_status()

        if status in (
            "exited",
            "stopped",
            "dead"
        ):

            try:
                all_logs = get_container_logs(10000)

                latest_new_logs = all_logs[
                    baseline_length:
                ]

            except Exception:
                pass

            return False, latest_new_logs

        try:

            all_logs = get_container_logs(10000)

            if len(all_logs) >= baseline_length:

                latest_new_logs = all_logs[
                    baseline_length:
                ]

            else:
                # Log rotation/truncation happened.
                latest_new_logs = all_logs

            if FORGE_READY_TEXT in latest_new_logs:

                return True, latest_new_logs

        except Exception:
            pass

        time.sleep(2)

    return False, latest_new_logs


# ============================================================
# Restart Worker
# ============================================================

def restart_worker():
    """
    Background restart sequence.

    RCON stop
        ->
    clean shutdown
        ->
    podman start
        ->
    wait for Forge Done
        ->
    Ready
    """

    try:

        # ----------------------------------------------------
        # Phase 1: Stopping
        # ----------------------------------------------------

        set_restart_state(
            in_progress=True,
            phase="stopping",
            message=(
                "Saving world and stopping Minecraft..."
            ),
            error=None
        )

        current_status = get_container_status()

        if current_status != "running":

            raise RuntimeError(
                "minecraft2 is not running. "
                f"Current status: {current_status}"
            )

        result = send_rcon("stop")

        # mcrcon can lose the RCON connection because Minecraft
        # closes RCON during shutdown. Therefore a non-zero
        # return code is not automatically treated as failure.

        if not wait_for_clean_stop():

            raise RuntimeError(
                "Minecraft did not stop cleanly within "
                f"{STOP_TIMEOUT} seconds. "
                "The server was NOT force-killed."
            )

        # ----------------------------------------------------
        # Phase 2: Starting container
        # ----------------------------------------------------

        set_restart_state(
            phase="starting",
            message=(
                "Minecraft stopped. Starting Forge..."
            )
        )

        podman(
            "start",
            CONTAINER
        )

        if not wait_for_container_running():

            raise RuntimeError(
                "minecraft2 failed to enter running state"
            )

        # ----------------------------------------------------
        # Phase 3: Waiting for Forge
        # ----------------------------------------------------

        set_restart_state(
            phase="waiting",
            message=(
                "Waiting for Forge startup..."
            )
        )

        ready, startup_logs = wait_for_forge_ready()

        if not ready:

            final_status = get_container_status()

            lines = (
                startup_logs
                .strip()
                .splitlines()
            )

            log_tail = "\n".join(
                lines[-20:]
            )

            raise RuntimeError(
                "Forge did not become Ready within "
                f"{FORGE_READY_TIMEOUT} seconds. "
                f"Container status: {final_status}\n\n"
                "Last startup logs:\n"
                f"{log_tail}"
            )

        # ----------------------------------------------------
        # Phase 4: Ready
        # ----------------------------------------------------

        set_restart_state(
            in_progress=False,
            phase="ready",
            message="Forge is Ready",
            error=None
        )

    except Exception as e:

        set_restart_state(
            in_progress=False,
            phase="failed",
            message="Restart failed",
            error=str(e)
        )


# ============================================================
# MOD Helpers
# ============================================================

def safe_mod_name(filename: str) -> str:

    if not filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is missing"
        )

    name = Path(filename).name

    if name in (
        "",
        ".",
        ".."
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )

    if not name.lower().endswith(".jar"):

        raise HTTPException(
            status_code=400,
            detail="Only .jar files are allowed"
        )

    return name


# ============================================================
# Display Status
# ============================================================

def get_display_status():
    """
    Return UI server status.
    """

    state = get_restart_state()

    if state["in_progress"]:

        phase = state["phase"]

        if phase == "stopping":
            return "Stopping..."

        if phase == "starting":
            return "Starting..."

        if phase == "waiting":
            return "Waiting for Forge..."

    if state["phase"] == "failed":

        return "Restart Failed"

    status = get_container_status()

    if status == "running":

        if is_forge_ready():
            return "Ready"

        return "Running / Starting"

    if status == "exited":
        return "Exited"

    if status == "stopped":
        return "Stopped"

    if status == "dead":
        return "Dead"

    return status.capitalize()


# ============================================================
# Web UI
# ============================================================

@app.get("/", response_class=HTMLResponse)
def index():

    return """
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0">

<title>Minecraft Forge Admin</title>

<style>

body {
    font-family: Arial, sans-serif;
    max-width: 900px;
    margin: 40px auto;
    padding: 20px;
    background: #f5f5f5;
}

.container {
    background: white;
    padding: 30px;
    border-radius: 10px;
}

h1 {
    margin-top: 0;
}

.section {
    margin-top: 30px;
}

hr {
    border: 0;
    border-top: 1px solid #ccc;
    margin: 35px 0;
}

.status-ready {
    color: green;
    font-weight: bold;
}

.status-running {
    color: #d68910;
    font-weight: bold;
}

.status-other {
    color: red;
    font-weight: bold;
}

button {
    padding: 8px 14px;
    margin: 4px;
    cursor: pointer;
}

button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.restart-button {
    background: #e67e22;
    color: white;
    border: none;
    border-radius: 4px;
}

.delete-button {
    background: #c0392b;
    color: white;
    border: none;
    border-radius: 4px;
}

.upload-button {
    background: #2980b9;
    color: white;
    border: none;
    border-radius: 4px;
}

li {
    margin: 8px 0;
}

pre {
    background: #222;
    color: #eee;
    padding: 15px;
    overflow: auto;
    max-height: 500px;
    white-space: pre-wrap;
    border-radius: 4px;
}

#message {
    margin-top: 15px;
    font-weight: bold;
}

</style>

</head>


<body>

<div class="container">

<h1>Minecraft Forge Admin</h1>


<!-- ===================================================== -->
<!-- Server -->
<!-- ===================================================== -->

<div class="section">

<h2>Server</h2>

<p>
Status:
<span id="status">
Loading...
</span>
</p>

<button
    class="restart-button"
    id="restartButton"
    onclick="restartServer()">

Restart Server

</button>

<div id="message"></div>

</div>


<hr>


<!-- ===================================================== -->
<!-- Mods -->
<!-- ===================================================== -->

<div class="section">

<h2>Mods</h2>

<ul id="mods">
</ul>

<h3>Upload MOD</h3>

<input
    type="file"
    id="file"
    accept=".jar">

<button
    class="upload-button"
    id="uploadButton"
    onclick="uploadMod()">

Upload

</button>

</div>


<hr>


<!-- ===================================================== -->
<!-- Server Log -->
<!-- ===================================================== -->

<div class="section">

<h2>Server Log</h2>

<button onclick="loadLogs()">
Refresh Log
</button>

<pre id="logs">
Loading...
</pre>

</div>


</div>


<script>


// ============================================================
// Status
// ============================================================

async function loadStatus() {

    try {

        const r =
            await fetch('/api/status');

        const data =
            await r.json();

        const status =
            document.getElementById(
                'status'
            );

        const message =
            document.getElementById(
                'message'
            );

        const restartButton =
            document.getElementById(
                'restartButton'
            );


        status.innerText =
            data.status;


        if (data.status === 'Ready') {

            status.className =
                'status-ready';

        } else if (
            data.in_progress ||
            data.status === 'Running / Starting'
        ) {

            status.className =
                'status-running';

        } else {

            status.className =
                'status-other';
        }


        restartButton.disabled =
            data.in_progress;


        if (
            data.message
        ) {

            message.innerText =
                data.message;
        }


        if (
            data.error
        ) {

            message.innerText =
                data.error;
        }


    } catch (error) {

        const status =
            document.getElementById(
                'status'
            );

        status.innerText =
            'Error';

        status.className =
            'status-other';
    }
}


// ============================================================
// Restart
// ============================================================

async function restartServer() {

    if (
        !confirm(
            'Restart minecraft2?\\n\\n' +
            'The world will be saved before restart.'
        )
    ) {

        return;
    }


    const button =
        document.getElementById(
            'restartButton'
        );

    const message =
        document.getElementById(
            'message'
        );


    button.disabled =
        true;

    message.innerText =
        'Starting restart...';


    try {

        const r =
            await fetch(
                '/api/restart',
                {
                    method: 'POST'
                }
            );


        const data =
            await r.json();


        if (!r.ok) {

            message.innerText =
                data.detail ||
                'Restart failed';

            button.disabled =
                false;

            return;
        }


        /*
         * Restart now runs in a background thread.
         *
         * The browser does NOT wait several minutes for
         * /api/restart.
         *
         * loadStatus() polls the current restart state.
         */

        message.innerText =
            data.message;


        await loadStatus();


    } catch (error) {

        message.innerText =
            'Restart request failed';

        button.disabled =
            false;
    }
}


// ============================================================
// MOD List
// ============================================================

async function loadMods() {

    try {

        const r =
            await fetch('/api/mods');

        const data =
            await r.json();

        const ul =
            document.getElementById(
                'mods'
            );

        ul.innerHTML =
            '';


        if (!r.ok) {

            const li =
                document.createElement(
                    'li'
                );

            li.innerText =
                'Unable to load MOD list';

            ul.appendChild(
                li
            );

            return;
        }


        if (data.mods.length === 0) {

            const li =
                document.createElement(
                    'li'
                );

            li.innerText =
                'No MOD files found';

            ul.appendChild(
                li
            );

            return;
        }


        data.mods.forEach(
            mod => {

                const li =
                    document.createElement(
                        'li'
                    );

                li.appendChild(
                    document.createTextNode(
                        mod + ' '
                    )
                );


                const button =
                    document.createElement(
                        'button'
                    );

                button.innerText =
                    'Delete';

                button.className =
                    'delete-button';


                button.onclick =
                    async () => {

                        if (
                            !confirm(
                                'Delete ' +
                                mod +
                                '?\\n\\n' +
                                'Server restart will be required.'
                            )
                        ) {
                            return;
                        }


                        const r =
                            await fetch(
                                '/api/mods/' +
                                encodeURIComponent(
                                    mod
                                ),
                                {
                                    method: 'DELETE'
                                }
                            );


                        const data =
                            await r.json();


                        if (!r.ok) {

                            alert(
                                data.detail ||
                                'Delete failed'
                            );

                            return;
                        }


                        document.getElementById(
                            'message'
                        ).innerText =
                            'Deleted: ' +
                            mod +
                            ' - Restart required';


                        await loadMods();
                    };


                li.appendChild(
                    button
                );

                ul.appendChild(
                    li
                );
            }
        );


    } catch (error) {

        console.error(
            error
        );
    }
}


// ============================================================
// MOD Upload
// ============================================================

async function uploadMod() {

    const input =
        document.getElementById(
            'file'
        );

    const button =
        document.getElementById(
            'uploadButton'
        );

    const file =
        input.files[0];


    if (!file) {

        alert(
            'Select a .jar file'
        );

        return;
    }


    if (
        !file.name
            .toLowerCase()
            .endsWith('.jar')
    ) {

        alert(
            'Only .jar files are allowed'
        );

        return;
    }


    const form =
        new FormData();

    form.append(
        'file',
        file
    );


    button.disabled =
        true;


    document.getElementById(
        'message'
    ).innerText =
        'Uploading...';


    try {

        const r =
            await fetch(
                '/api/mods/upload',
                {
                    method: 'POST',
                    body: form
                }
            );


        const data =
            await r.json();


        if (!r.ok) {

            document.getElementById(
                'message'
            ).innerText =
                'Upload failed: ' +
                (
                    data.detail ||
                    'Unknown error'
                );

            return;
        }


        document.getElementById(
            'message'
        ).innerText =
            'Uploaded: ' +
            data.filename +
            ' - Restart required';


        input.value =
            '';


        await loadMods();


    } catch (error) {

        document.getElementById(
            'message'
        ).innerText =
            'Upload failed';

    } finally {

        button.disabled =
            false;
    }
}


// ============================================================
// Logs
// ============================================================

async function loadLogs() {

    try {

        const r =
            await fetch(
                '/api/logs'
            );

        const data =
            await r.json();


        if (!r.ok) {

            document.getElementById(
                'logs'
            ).innerText =
                data.detail ||
                'Unable to load logs';

            return;
        }


        const logElement =
            document.getElementById(
                'logs'
            );


        logElement.innerText =
            data.logs;


        logElement.scrollTop =
            logElement.scrollHeight;


    } catch (error) {

        document.getElementById(
            'logs'
        ).innerText =
            'Unable to load logs';
    }
}


// ============================================================
// Initial Load
// ============================================================

loadStatus();

loadMods();

loadLogs();


/*
 * During restart this gives near-real-time GUI updates:
 *
 * Stopping...
 * Starting...
 * Waiting for Forge...
 * Ready
 */

setInterval(
    loadStatus,
    2000
);


/*
 * Refresh logs every 5 seconds.
 */

setInterval(
    loadLogs,
    5000
);


</script>

</body>

</html>
"""


# ============================================================
# API: Status
# ============================================================

@app.get("/api/status")
def status():

    state = get_restart_state()

    return {
        "status": get_display_status(),
        "in_progress": state["in_progress"],
        "phase": state["phase"],
        "message": state["message"],
        "error": state["error"]
    }


# ============================================================
# API: Restart
# ============================================================

@app.post("/api/restart")
def restart():

    if not RCON_PASS:

        raise HTTPException(
            status_code=500,
            detail="MCRCON_PASS is not configured"
        )


    with restart_lock:

        if restart_state["in_progress"]:

            raise HTTPException(
                status_code=409,
                detail=(
                    "A restart is already in progress"
                )
            )

        restart_state["in_progress"] = True
        restart_state["phase"] = "stopping"
        restart_state["message"] = (
            "Saving world and stopping Minecraft..."
        )
        restart_state["error"] = None


    worker = threading.Thread(
        target=restart_worker,
        daemon=True
    )

    worker.start()


    return {
        "message": (
            "Saving world and stopping Minecraft..."
        ),
        "status": "accepted"
    }


# ============================================================
# API: MOD List
# ============================================================

@app.get("/api/mods")
def mods():

    try:

        files = sorted(
            p.name
            for p in MOD_DIR.iterdir()
            if (
                p.is_file()
                and p.suffix.lower() == ".jar"
            )
        )

        return {
            "mods": files
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# API: Upload MOD
# ============================================================

@app.post("/api/mods/upload")
def upload(
    file: UploadFile = File(...)
):

    name = safe_mod_name(
        file.filename
    )

    destination = (
        MOD_DIR / name
    )


    if destination.exists():

        raise HTTPException(
            status_code=409,
            detail=(
                "A MOD with this filename "
                "already exists"
            )
        )


    try:

        total_size = 0


        with destination.open(
            "wb"
        ) as output:

            while True:

                chunk = file.file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_size += len(
                    chunk
                )

                if (
                    total_size
                    > MAX_UPLOAD_SIZE
                ):

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File is too large. "
                            "Maximum size is 500 MB."
                        )
                    )

                output.write(
                    chunk
                )


        return {
            "message": "uploaded",
            "filename": name,
            "restart_required": True
        }


    except HTTPException:

        if destination.exists():
            destination.unlink()

        raise


    except Exception as e:

        if destination.exists():
            destination.unlink()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


    finally:

        file.file.close()


# ============================================================
# API: Delete MOD
# ============================================================

@app.delete("/api/mods/{filename}")
def delete_mod(
    filename: str
):

    name = safe_mod_name(
        filename
    )

    target = (
        MOD_DIR / name
    )


    if not target.exists():

        raise HTTPException(
            status_code=404,
            detail="MOD not found"
        )


    if not target.is_file():

        raise HTTPException(
            status_code=400,
            detail="Invalid MOD"
        )


    try:

        target.unlink()

        return {
            "message": "deleted",
            "filename": name,
            "restart_required": True
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# API: Logs
# ============================================================

@app.get("/api/logs")
def logs():

    try:

        output = get_container_logs(
            150
        )

        return {
            "logs": output
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
