# How to deploy a container for web administration 
Minecraft-forgeのアドミン用のwebサーバを構築する手順
<br>
<br>

## Requirements
- SSHクライアント(e.g.PowerShell)
- 

                  Internet
                     │
          ┌──────────┴──────────┐
          │                     │
       TCP 443              TCP 25566
       Admin Web            Minecraft
          │                     │
          ▼                     ▼
       Caddy                minecraft2
          │                 Forge 1.20.1
       認証
          │
          ▼
      Admin Web
       │     │
       │     └── Restart / Status / Logs
       │
       └── MOD Upload
              │
              ▼
 /home/opc/minecraft/server2/mods
              │
              ▼
          minecraft2


┌────────────────────────────────────┐
│ Minecraft Forge Server             │
│                                    │
│ Status: ● Running                  │
│ Players: 2 / 10                    │
│                                    │
│ [ Restart Server ]  [ Stop ]       │
│                                    │
│ Mods                               │
│ ────────────────────────────────   │
│ jei-1.20.1.jar          [Delete]   │
│ journeymap-1.20.1.jar   [Delete]   │
│ create-1.20.1.jar       [Delete]   │
│                                    │
│ Upload MOD                         │
│ [ Choose File ]                    │
│ [ Upload ]                         │
│                                    │
│ Server Log                         │
│ ────────────────────────────────   │
│ Starting Minecraft server...       │
│ Done (8.24s)!                      │
└────────────────────────────────────┘


<br>
<br>

## Table of Contents
注：手順1~は、外部公開せずにOCI VM上で管理Webを作り、① MOD一覧 → ② .jarアップロード → ③ 削除 → ④ minecraft2再起動 → ⑤ 状態確認を検証する。


[1. Preparation](#1-Preparation)  
[2. Create Web application](#2-Create-Web-application)  
[3. Check mods directory](#3-Check-mods-directory)    
[4. Run FastAPI](#4-Run-FastAPI)  
[5. Enable whitelist](#5-Enable-whitelist)  
[6. Install RCON](#6-Install-RCON)  

<br>
<br>

## 1. Preparation 
- ディレクトリを作る
```
mkdir -p /home/opc/minecraft/admin-web
cd /home/opc/minecraft/admin-web
```

- pythonの確認
```
python3 --version
```

- 仮想化環境の作成
```
sudo dnf install -y python3-pip
python3 -m venv venv
source venv/bin/activate
```

- FastAPIのインストール
```
pip install fastapi uvicorn python-multipart
```
<br>
<br>

## 2. Create Web application 
- アプリのコードを作成
```
vi /home/opc/minecraft/admin-web/app.py
```
```
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from pathlib import Path
import subprocess
import shutil

app = FastAPI()

MOD_DIR = Path("/home/opc/minecraft/server2/mods")
CONTAINER = "minecraft2"

MOD_DIR.mkdir(parents=True, exist_ok=True)


def podman(*args):
    result = subprocess.run(
        ["podman", *args],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def safe_mod_name(filename: str) -> str:
    # Directory部分を除去
    name = Path(filename).name

    if not name.lower().endswith(".jar"):
        raise HTTPException(
            status_code=400,
            detail="Only .jar files are allowed"
        )

    if name in ("", ".", ".."):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename"
        )

    return name


@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Minecraft Forge Admin</title>

<style>
body {
    font-family: sans-serif;
    max-width: 900px;
    margin: 40px auto;
    padding: 20px;
}

button {
    padding: 8px 14px;
    margin: 4px;
}

#status {
    font-weight: bold;
}

li {
    margin: 8px 0;
}

pre {
    background: #eee;
    padding: 15px;
    overflow: auto;
    max-height: 400px;
}
</style>
</head>

<body>

<h1>Minecraft Forge Admin</h1>

<h2>Server</h2>

<p>Status: <span id="status">Loading...</span></p>

<button onclick="restartServer()">Restart Server</button>

<h2>Mods</h2>

<ul id="mods"></ul>

<h3>Upload MOD</h3>

<input type="file" id="file" accept=".jar">
<button onclick="uploadMod()">Upload</button>

<h2>Server Log</h2>

<button onclick="loadLogs()">Refresh Log</button>

<pre id="logs"></pre>


<script>

async function loadStatus() {
    const r = await fetch('/api/status');
    const data = await r.json();
    document.getElementById('status').innerText = data.status;
}


async function loadMods() {
    const r = await fetch('/api/mods');
    const data = await r.json();

    const ul = document.getElementById('mods');
    ul.innerHTML = '';

    data.mods.forEach(mod => {

        const li = document.createElement('li');

        li.appendChild(
            document.createTextNode(mod + ' ')
        );

        const button = document.createElement('button');

        button.innerText = 'Delete';

        button.onclick = async () => {

            if (!confirm('Delete ' + mod + '?')) {
                return;
            }

            await fetch(
                '/api/mods/' + encodeURIComponent(mod),
                {method:'DELETE'}
            );

            loadMods();
        };

        li.appendChild(button);

        ul.appendChild(li);
    });
}


async function uploadMod() {

    const file =
        document.getElementById('file').files[0];

    if (!file) {
        alert('Select a .jar file');
        return;
    }

    const form = new FormData();

    form.append('file', file);

    const r = await fetch(
        '/api/mods/upload',
        {
            method:'POST',
            body:form
        }
    );

    const data = await r.json();

    if (!r.ok) {
        alert(data.detail);
        return;
    }

    alert('Uploaded: ' + data.filename);

    loadMods();
}


async function restartServer() {

    if (!confirm('Restart minecraft2?')) {
        return;
    }

    const r = await fetch(
        '/api/restart',
        {method:'POST'}
    );

    const data = await r.json();

    alert(data.message);

    setTimeout(loadStatus, 3000);
}


async function loadLogs() {

    const r = await fetch('/api/logs');

    const data = await r.json();

    document.getElementById('logs').innerText =
        data.logs;
}


loadStatus();
loadMods();
loadLogs();

</script>

</body>
</html>
"""


@app.get("/api/status")
def status():
    try:
        value = podman(
            "inspect",
            "-f",
            "{{.State.Status}}",
            CONTAINER
        )

        return {"status": value}

    except Exception as e:
        return {"status": "unknown", "error": str(e)}


@app.get("/api/mods")
def mods():
    files = sorted(
        p.name
        for p in MOD_DIR.iterdir()
        if p.is_file() and p.suffix.lower() == ".jar"
    )

    return {"mods": files}


@app.post("/api/mods/upload")
def upload(file: UploadFile = File(...)):

    name = safe_mod_name(file.filename)

    destination = MOD_DIR / name

    # Phase 1では既存MODの上書きを禁止
    if destination.exists():
        raise HTTPException(
            status_code=409,
            detail="A file with this name already exists"
        )

    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    return {
        "message": "uploaded",
        "filename": name
    }


@app.delete("/api/mods/{filename}")
def delete_mod(filename: str):

    name = safe_mod_name(filename)

    target = MOD_DIR / name

    if not target.exists():
        raise HTTPException(
            status_code=404,
            detail="MOD not found"
        )

    target.unlink()

    return {
        "message": "deleted",
        "filename": name
    }


@app.post("/api/restart")
def restart():

    try:
        podman(
            "restart",
            "--time",
            "30",
            CONTAINER
        )

        return {
            "message": "minecraft2 restarted"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/api/logs")
def logs():

    try:
        output = podman(
            "logs",
            "--tail",
            "100",
            CONTAINER
        )

        return {"logs": output}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
```

<br>
<br>

## 3. Check mods directory
- server2のmodディレクトリを確認
```
podman unshare ls -ld /home/opc/minecraft/server2/mods
```

## 4. Run FastAPI
注：この時点ではインターネットに公開しない
- 
```
cd /home/opc/minecraft/admin-web
source venv/bin/activate
```

- FastAPIの起動
```
uvicorn app:app \
  --host 127.0.0.1 \
  --port 8080
```

<br>
<br>

## 5. Checking access
注：自分のPCのブラウザからSSHトンネルでアクセス
- SSHトンネルの作成
```
ssh -i ~/.ssh/ssh-key-oci.key -L 8080:127.0.0.1:8080 opc@<OCI-Public-IP>
```
- PCのブラウザで以下にアクセス (管理画面が見えればOK)
```
http://127.0.0.1:8080
```
- 動作確認 (以下が表示されればOK)
```
Minecraft Forge Admin

Server
Status: running

[Restart Server]

Mods
...

Upload MOD
[Choose File] [Upload]

Server Log
...
```
- restart serverのテスト (Forgeが再起動すればOK)
```
Restart serverをクリック
```

