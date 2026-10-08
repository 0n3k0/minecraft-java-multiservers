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
- 構文チェック
```
cd /home/opc/minecraft/admin-web
source venv/bin/activate

python -m py_compile app.py
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

