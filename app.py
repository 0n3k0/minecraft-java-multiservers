from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import subprocess
import os
import time


# ============================================================
# Configuration
# ============================================================

app = FastAPI()

# Forge server2 data directory
MOD_DIR = Path("/home/opc/minecraft/server2/mods")

# Podman container name
CONTAINER = "minecraft2"

# RCON configuration
RCON_HOST = "127.0.0.1"
RCON_PORT = "25576"
RCON_PASS = os.environ.get("MCRCON_PASS")

# Maximum MOD upload size: 500 MB
MAX_UPLOAD_SIZE = 500 * 1024 * 1024

# Maximum time to wait for clean shutdown
STOP_TIMEOUT = 120

# Maximum time to wait for Forge to become Ready
FORGE_READY_TIMEOUT = 300

# Forge startup completion string
FORGE_READY_TEXT = 'For help, type "help"'

MOD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Utility Functions
# ============================================================

def podman(*args, timeout=30):
    """
    Execute a Podman command and return stdout.
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
    Return Podman container status.
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


def get_container_started_at():
    """
    Return the current container start time in RFC3339 format.

    Example:
        2026-10-08T00:12:34.123456789Z

    This value changes each time the container is started.
    """

    try:
        started_at = podman(
            "inspect",
            "-f",
            "{{.State.StartedAt}}",
            CONTAINER
        )

        if not started_at:
            return None

        # Podman may return the zero-value timestamp if the
        # container has never been started.
        if started_at.startswith("0001-01-01"):
            return None

        return started_at

    except Exception:
        return None


def get_logs_since(timestamp: str):
    """
    Return container logs generated since timestamp.

    stdout and stderr are combined because container log
    output may appear on either stream.
    """

    result = subprocess.run(
        [
            "podman",
            "logs",
            "--since",
            timestamp,
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

    output = ""

    if result.stdout:
        output += result.stdout

    if result.stderr:
        output += result.stderr

    return output


def get_current_startup_logs():
    """
    Return logs belonging only to the current container run.

    The container's actual StartedAt timestamp is obtained
    from Podman, so old Forge startup logs are excluded.
    """

    started_at = get_container_started_at()

    if not started_at:
        return ""

    return get_logs_since(started_at)


def is_forge_ready():
    """
    Determine whether the CURRENT Forge instance is Ready.

    Old 'Done' messages from previous runs are ignored.
    """

    if get_container_status() != "running":
        return False

    try:
        logs = get_current_startup_logs()

        return FORGE_READY_TEXT in logs

    except Exception:
        return False


def safe_mod_name(filename: str) -> str:
    """
    Validate MOD filename.
    """

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing"
        )

    name = Path(filename).name

    if name in ("", ".", ".."):
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


def send_rcon(command: str):
    """
    Send command to Minecraft through localhost-only RCON.
    """

    if not RCON_PASS:
        raise RuntimeError(
            "MCRCON_PASS is not configured"
        )

    result = subprocess.run(
        [
            "mcrcon",
            "-H", RCON_HOST,
            "-P", RCON_PORT,
            "-p", RCON_PASS,
            command
        ],
        capture_output=True,
        text=True,
        timeout=10
    )

    # The "stop" command can close the RCON connection while
    # mcrcon is still waiting for a response. Therefore the
    # return code alone is not used as shutdown success.
    return result


def wait_for_clean_stop():
    """
    Wait until the container exits after Minecraft receives
    the RCON stop command.
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


def wait_for_forge_ready():
    """
    Wait until the CURRENT Forge startup emits its Ready text.

    The Podman StartedAt value is used to ensure that only
    logs from the current container run are inspected.

    Returns:
        (True, logs)
        (False, logs)
    """

    deadline = time.time() + FORGE_READY_TIMEOUT
    last_logs = ""

    while time.time() < deadline:

        status = get_container_status()

        # Forge/container crashed during startup.
        if status in (
            "exited",
            "stopped",
            "dead"
        ):

            try:
                last_logs = get_current_startup_logs()
            except Exception:
                pass

            return False, last_logs

        if status == "running":

            try:
                last_logs = get_current_startup_logs()

                if FORGE_READY_TEXT in last_logs:
                    return True, last_logs

            except Exception:
                # Container may have only just started.
                # Retry rather than immediately failing.
                pass

        time.sleep(2)

    return False, last_logs


def get_display_status():
    """
    Return the status displayed by the Web UI.

    Ready:
        Container is running AND the current startup logs
        contain Forge's Ready message.

    Running / Starting:
        Container is running but current Forge startup has
        not reached Ready yet.

    Exited / Stopped / Dead / Unknown:
        Container is not running.
    """

    container_status = get_container_status()

    if container_status == "running":

        if is_forge_ready():
            return "Ready"

        return "Running / Starting"

    if container_status == "exited":
        return "Exited"

    if container_status == "stopped":
        return "Stopped"

    if container_status == "dead":
        return "Dead"

    return container_status.capitalize()


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
// Server Status
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

        status.innerText =
            data.status;


        if (data.status === 'Ready') {

            status.className =
                'status-ready';

        } else if (
            data.status === 'Running / Starting'
        ) {

            status.className =
                'status-running';

        } else {

            status.className =
                'status-other';
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

        ul.innerHTML = '';


        if (!r.ok) {

            const li =
                document.createElement(
                    'li'
                );

            li.innerText =
                'Unable to load MOD list';

            ul.appendChild(li);

            return;
        }


        if (data.mods.length === 0) {

            const li =
                document.createElement(
                    'li'
                );

            li.innerText =
                'No MOD files found';

            ul.appendChild(li);

            return;
        }


        data.mods.forEach(mod => {

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
        });

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
// Safe Restart
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

    const status =
        document.getElementById(
            'status'
        );


    button.disabled =
        true;


    status.innerText =
        'Restarting...';

    status.className =
        'status-running';


    document.getElementById(
        'message'
    ).innerText =
        'Saving world and stopping Minecraft...';


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

            status.innerText =
                'Restart Failed';

            status.className =
                'status-other';


            document.getElementById(
                'message'
            ).innerText =
                'Restart failed: ' +
                (
                    data.detail ||
                    'Unknown error'
                );


            await loadLogs();

            return;
        }


        /*
         * /api/restart returns success only after the
         * CURRENT Forge startup emits its Ready message.
         */

        status.innerText =
            'Ready';

        status.className =
            'status-ready';


        document.getElementById(
            'message'
        ).innerText =
            'Forge is Ready';


        await loadLogs();

    } catch (error) {

        status.innerText =
            'Error';

        status.className =
            'status-other';


        document.getElementById(
            'message'
        ).innerText =
            'Restart request failed';

    } finally {

        button.disabled =
            false;

        /*
         * Re-read the authoritative server status after
         * restart processing has completed.
         */
        await loadStatus();
    }
}


// ============================================================
// Server Logs
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


// Refresh authoritative status every 10 seconds.

setInterval(
    loadStatus,
    10000
);


</script>

</body>

</html>
"""


# ============================================================
# API: Server Status
# ============================================================

@app.get("/api/status")
def status():
    """
    Return Forge status based on the CURRENT container run.

    Old Done messages from previous starts are not used.
    """

    return {
        "status": get_display_status()
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

    destination = MOD_DIR / name


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


                total_size += len(chunk)


                if total_size > MAX_UPLOAD_SIZE:

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

    target = MOD_DIR / name


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
# API: Safe Restart + Current Forge Ready Check
# ============================================================

@app.post("/api/restart")
def restart():

    if not RCON_PASS:

        raise HTTPException(
            status_code=500,
            detail=(
                "MCRCON_PASS is not configured"
            )
        )


    current_status = (
        get_container_status()
    )


    if current_status != "running":

        raise HTTPException(
            status_code=409,
            detail=(
                "minecraft2 is not running. "
                "Current status: "
                + current_status
            )
        )


    try:

        # ====================================================
        # STEP 1
        #
        # Ask Minecraft/Forge itself to stop.
        #
        # This allows Minecraft to save players, worlds,
        # chunks and MOD state before Java exits.
        # ====================================================

        send_rcon(
            "stop"
        )


        # ====================================================
        # STEP 2
        #
        # Wait for a clean container exit.
        #
        # Do NOT automatically SIGKILL if shutdown fails.
        # ====================================================

        if not wait_for_clean_stop():

            raise RuntimeError(
                "Minecraft did not stop "
                "cleanly within "
                f"{STOP_TIMEOUT} seconds. "
                "The server was NOT force-killed."
            )


        # ====================================================
        # STEP 3
        #
        # Start the same minecraft2 container.
        # ====================================================

        podman(
            "start",
            CONTAINER
        )


        # ====================================================
        # STEP 4
        #
        # Wait until Forge becomes Ready.
        #
        # wait_for_forge_ready() obtains the container's
        # current .State.StartedAt timestamp and only examines
        # logs generated since that start.
        #
        # Therefore a Done message from an older Forge run
        # cannot cause a false Ready result.
        # ====================================================

        ready, startup_logs = (
            wait_for_forge_ready()
        )


        # ====================================================
        # STEP 5
        #
        # Forge failed to become Ready.
        # ====================================================

        if not ready:

            final_status = (
                get_container_status()
            )


            log_lines = (
                startup_logs
                .strip()
                .splitlines()
            )


            log_tail = "\n".join(
                log_lines[-20:]
            )


            raise RuntimeError(
                "Forge did not become Ready "
                f"within {FORGE_READY_TIMEOUT} "
                "seconds. "
                "Container status: "
                f"{final_status}\n\n"
                "Last startup logs:\n"
                f"{log_tail}"
            )


        # ====================================================
        # STEP 6
        #
        # Final authoritative verification.
        #
        # Do not return Ready unless the current container run
        # still satisfies the same Ready test.
        # ====================================================

        if not is_forge_ready():

            raise RuntimeError(
                "Forge Ready message was detected, "
                "but final Ready verification failed."
            )


        # ====================================================
        # STEP 7
        #
        # Success.
        # ====================================================

        return {
            "message": "Forge is Ready",
            "status": "Ready"
        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# API: Server Logs
# ============================================================

@app.get("/api/logs")
def logs():

    try:

        output = podman(
            "logs",
            "--tail",
            "150",
            CONTAINER
        )


        return {
            "logs": output
        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
