# How to build Minecraft Container and deploy it 
Minecraftコンテナ(バニラ)を作成しOCI(Oracle Linux9)にコンテナをデプロイする手順
<br>
<br>

## Requirements
- SSHクライアント(e.g.PowerShell)
- Java 1.25
- Minecraft server.26.3 (https://www.minecraft.net/ja-jp/download/server)
<br>
<br>

## Table of Contents
[1. Create a image](#1-Create-a-image)  
[2. Create EULA file](#2-Create-EULA-file)  
[3. Run Minecraft container](#3-Run-Minecraft-container)  
[4. Change configuration](#4-Change-configuration)  
[5. Enable whitelist](#5-Enable-whitelist)  
[6. Install RCON](#6-Install-RCON)  

<br>
<br>

## 1. Create a image  
- ディレクトリを作る
 <img width="160" height="171" alt="image" src="https://github.com/user-attachments/assets/944febf3-d8ee-4609-ae24-aaca512aad26" />

   ```
   mkdir -p ~/minecraft/image1
   mkdir -p ~/minecraft/server1
   mkdir -p ~/minecraft/server2
   cd ~/minecraft 
  ```
- Minecraft server.jarを取得し保存
 (https://piston-data.mojang.com/v1/objects/33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c/server.jar)
   ```
   cd ~/minecraft/image/
   wget https://piston-data.mojang.com/v1/objects/33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c/server.jar
   ```  

- Containerfileを作る 
  ```
  cd ~/minecraft/image1
  vi Containerfile 
  ```
- dockerfileを作成  
  ```
  FROM container-registry.oracle.com/os/oraclelinux:9

  RUN dnf -y update && \
      dnf -y install java-25-openjdk-headless && \
      dnf clean all && \
      rm -rf /var/cache/dnf

  RUN useradd -r -m -d /minecraft minecraft

  WORKDIR /minecraft

  COPY server.jar /opt/minecraft/server.jar

  RUN chown -R minecraft:minecraft /minecraft /opt/minecraft

  USER minecraft

  EXPOSE 25565

  ENTRYPOINT ["java"]
  CMD ["-jar", "/opt/minecraft/server.jar", "nogui"] 
  ```
 
- コンテナイメージをBuild  
  ```
  cd ~/minecraft/image
  podman build -t minecraft-server.26.3:latest . 
  ```

  - コンテナイメージの確認  
  ```
  podman images 
  ```

  - javaの確認 
  ```
  podman run --rm \
  --entrypoint java \
  localhost/minecraft-server:latest \
  -version 
  ```
<br>
<br>

## 2. Create EULA file
  - EULAファイルを作成
  ```
  echo "eula=true" > ~/minecraft/server1/eula.txt
  ```
<br>
<br>

## 3. Run Minecraft container
  - コンテナを起動
  ```
  podman run -d \
  --name minecraft1 \
  --memory=10g \
  -p 25565:25565 \
  -p 127.0.0.1:25575:25575 \
  -v ~/minecraft/server1:/minecraft:Z,U \
  localhost/minecraft-server.26.3:latest \
  -Xms4G \
  -Xmx8G \
  -jar /opt/minecraft/server.jar \
  nogui 
  ```
 
  - コンテナを確認
  ```
  podman ps
  podman logs -f minecraft1
  ```

  - コンテナを停止/削除する場合
  ```
  podman stop minecraft1
  podman rm minecraft1
  ```

  - cpu/mem確認
  ```
  podman stats
  ```
<br>
<br>

## 4. Change configuration
  - server.propertiesを変更 (初回起動後)
  ```
  sudo vi ~/minecraft/server1/server.properties 
  ```
  ```
  # 接続
  online-mode=true
  max-players=10

  # ゲーム
  gamemode=survival
  difficulty=normal

  # World
  spawn-protection=16

  # Performance
  view-distance=8
  simulation-distance=6

  # Server list
  motd=OCI Minecraft Server 1
  ```
<br>
<br>

## 5. Enable whitelist
  - Whitelistを有効化
  ```
  podman exec minecraft1 sed -i 's/^white-list=.*/white-list=true/' /minecraft/server.properties

  podman exec minecraft1 sed -i 's/^enforce-whitelist=.*/enforce-whitelist=true/' /minecraft/server.properties 
  ```

  - RCONパスワードを設定
  ```
  podman exec minecraft1 sed -i 's/^enable-rcon=.*/enable-rcon=true/' /minecraft/server.properties

podman exec minecraft1 sed -i 's/^rcon.password=.*/rcon.password=YOUR_STRONG_PASSWORD/' /minecraft/server.properties 
  ```

- 確認
  ```
  podman exec minecraft1 grep -E '^(enable-rcon|rcon.port)=' /minecraft/server.properties 
  ```

- 起動
  ```
  podman run -d \
  --name minecraft1 \
  --memory=10g \
  -p 25565:25565 \
  -p 127.0.0.1:25575:25575 \
  -v ~/minecraft/server1:/minecraft:Z,U \
  localhost/minecraft-server.26.3:latest \
  -Xms4G \
  -Xmx8G \
  -jar /opt/minecraft/server.jar \
  nogui 
  ```
  ```
  podman port minecraft1
  ```
<br>
<br>

## 6. Install RCON
  - mcrcon をインストール
  ```
  sudo dnf install -y git gcc make 
  ```
  ```
  cd /tmp
  git clone https://github.com/Tiiffi/mcrcon.git
  cd mcrcon
  make
  sudo install -m 755 mcrcon /usr/local/bin/mcrcon
  ```
  - 確認
  ```
  mcrcon -v
  ```
  - RCON接続をテスト
  ```
  mcrcon -H 127.0.0.1 -P 25575 -p 'MY PASSWORD' "list"
  ```



