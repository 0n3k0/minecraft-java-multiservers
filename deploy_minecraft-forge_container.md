# How to build Minecraft forge container and deploy it 
Minecraft forge鯖(コンテナ)をたてる手順

---
## Requirements
- SSHクライアント(e.g.PowerShell)
- Java 1.17
- Minecraft-forge 1.20.1 

---
## 1.Create Containerfile  
- ディレクトリ作成
  ```
  mkdir -p ~/minecraft/image2
  cd ~/minecraft/image2
  ```
- イメージの確認
   ```
   podman image inspect \
   container-registry.oracle.com/os/oraclelinux:9 \
   --format '{{.Architecture}}'
   ```  
- Containerfileの作成
```
vi Containerfile
```
```
FROM container-registry.oracle.com/os/oraclelinux:9

ARG FORGE_VERSION=1.20.1-47.4.13

# Java 17 + required packages
RUN dnf -y update && \
    dnf -y install \
        java-17-openjdk \
        wget \
        shadow-utils \
        findutils \
        && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Minecraft dedicated user
RUN useradd -r \
    -m \
    -d /home/minecraft \
    -s /bin/bash \
    minecraft

# ---------------------------------------------------
# Forge template
# ---------------------------------------------------

RUN mkdir -p /opt/forge-template

WORKDIR /opt/forge-template

# Forge installer download
RUN wget \
    https://files.minecraftforge.net/maven/net/minecraftforge/forge/${FORGE_VERSION}/forge-${FORGE_VERSION}-installer.jar

# Forge installation
RUN java \
    -jar forge-${FORGE_VERSION}-installer.jar \
    --installServer

# Remove installer
RUN rm -f \
    forge-${FORGE_VERSION}-installer.jar \
    forge-${FORGE_VERSION}-installer.jar.log

# JVM settings
RUN printf '%s\n' \
    '-XX:+UnlockExperimentalVMOptions' \
    '-Xms4G' \
    '-Xmx8G' \
    '-XX:+UseG1GC' \
    '-XX:MaxGCPauseMillis=200' \
    '-XX:+ParallelRefProcEnabled' \
    '-XX:G1NewSizePercent=20' \
    '-XX:G1MaxNewSizePercent=45' \
    '-XX:G1ReservePercent=20' \
    '-XX:G1HeapRegionSize=16M' \
    '-XX:+AlwaysPreTouch' \
    '-Dfile.encoding=UTF-8' \
    > user_jvm_args.txt

# EULA
# Build/use only after reviewing and accepting the Minecraft EULA.
RUN printf 'eula=true\n' > eula.txt

# ---------------------------------------------------
# Runtime data directory
# ---------------------------------------------------

RUN mkdir -p /minecraft

COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod 755 /usr/local/bin/entrypoint.sh && \
    chown -R minecraft:minecraft \
        /opt/forge-template \
        /minecraft

USER minecraft

WORKDIR /minecraft

EXPOSE 25565

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
```

- entrypoint.shの作成
```
vi entrypoint.sh
```
```
#!/bin/bash
set -e

TEMPLATE=/opt/forge-template
DATA=/minecraft

echo "Minecraft Forge container starting..."

# --------------------------------------------------
# First boot
# --------------------------------------------------

if [ ! -f "${DATA}/run.sh" ]; then

    echo "Initializing Minecraft Forge server data..."

    cp -a "${TEMPLATE}/." "${DATA}/"

    echo "Initialization completed."

fi

# --------------------------------------------------
# Start Forge
# --------------------------------------------------

cd "${DATA}"

echo "Starting Minecraft Forge..."

exec ./run.sh nogui
```
- 実行権限
```
chmod +x entrypoint.sh
```



---
## 2.Build a image  
- イメージのビルド
  ```
  cd ~/minecraft/image2
  ```
  ```
  podman build \
  --no-cache \
  -t minecraft-forge-server-1.20.1 \
  .
  ```
  ```
  podman images
  ```

---
## 3.Run the image  
  - server2用永続ディレクトリの作成
  ```
  mkdir -p /home/opc/minecraft/server2
  ls -la /home/opc/minecraft/server2
  ```
  - server2として起動
  ```
  podman run -d \
  --name minecraft2 \
  -p 25566:25565 \
  -v /home/opc/minecraft/server2:/minecraft:Z,U \
  localhost/minecraft-forge-server-1.20.1:latest
  ```
  - 停止
  ```
  podman stop minecraft2
  podman rm minecraft2
  ```

---
## 4.Copy Backup data  
  - 現在のworldを念のため退避
  ```
  sudo mv \
  /home/opc/minecraft/server2/world \
  /home/opc/minecraft/server2/world.old
  ```

  - バックアップをコピー
  ```
  sudo cp -a \
  /opt/minecraft/world \
  /home/opc/minecraft/server2/world
  ```

---
## 5.Install Mod files  
  - modファイルをコピー
  ```
  sudo cp /home/opc/mods/* ~/minecraft/server2/mods
  ```

---
## 6.Configure SELinux  
  - 現在のSELinux状態を確認(おそらくEnforcing)
  ```
  getenforce
  ```
  - ディレクトリのラベルも確認
  ```
  ls -Zd /home/opc/minecraft/server2
  ls -Z /home/opc/minecraft/server2/mods/ | head
  ```
  - コンテナ用SELinuxラベルを設定
  ```
  sudo chcon -Rt container_file_t /home/opc/minecraft/server2
  ```
  - 確認 (container_file_t が付いていればOK)
  ```
  system_u:object_r:container_file_t:s0 /home/opc/minecraft/server2
  ```
  - uidの確認 (おそらくuid=999(minecraft) gid=999(minecraft)と表示)
  ```
  podman run --rm \
  --entrypoint id \
  localhost/minecraft-forge-server-1.20.1:latest
  ```
  - rootless Podman用の所有権を変更
  ```
  podman unshare chown -R 999:999 /home/opc/minecraft/server2
  ```
  ```
  sudo chown -R opc:opc /home/opc/minecraft/server2
  ls -ln /home/opc/minecraft/server2/mods/ | head
  sudo chcon -Rt container_file_t /home/opc/minecraft/server2
  ls -Zd /home/opc/minecraft/server2
  ls -lZ /home/opc/minecraft/server2/mods/ | head
  podman run --rm \
  --entrypoint id \
  localhost/minecraft-forge-server-1.20.1:latest
  podman unshare chown -R 995:995 /home/opc/minecraft/server2
　podman unshare rm -f /home/opc/minecraft/server2/podman-test
  ls -l /home/opc/minecraft/server2/podman-test
  podman rm -f minecraft2 2>/dev/null || true
  podman unshare ls -ldn /home/opc/minecraft/server2
  podman run --rm \
  -v /home/opc/minecraft/server2:/minecraft:Z \
  --entrypoint /bin/bash \
  localhost/minecraft-forge-server-1.20.1:latest \
  -c 'id; ls -ldZ /minecraft; touch /minecraft/selinux-test && rm /minecraft/selinux-test'
  ```

---
## 7.Run Minecraft-forge server  
  - server2として起動
  ```
  podman run -d \
  --name minecraft2 \
  -p 25566:25565 \
  -v /home/opc/minecraft/server2:/minecraft:Z \
  localhost/minecraft-forge-server-1.20.1:latest
  ```
  - 停止
  ```
  podman stop minecraft2
  podman rm minecraft2
  ```

---
## 8.Configure systemd  
  - opcをログアウトしてもuser systemdを維持するように設定
  ```
  sudo loginctl enable-linger opc
  ```
  - 確認（Linger=yesならOK)
  ```
  loginctl show-user opc -p Linger
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
  podman build -t minecraft-server:latest . 
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

## 5.Create EULA files
  - EULAファイルを作成
  ```
  echo "eula=true" > ~/minecraft/server1/eula.txt
  echo "eula=true" > ~/minecraft/server2/eula.txt 
  ```

## 6.Run Minecraft#1
  - コンテナを起動
  ```
  podman run -d \
  --name minecraft1 \
  --memory=10g \
  -p 25565:25565 \
  -v ~/minecraft/server1:/minecraft:Z,U \
  localhost/minecraft-server:latest \
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

## 7.Change configurations
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




---
## 3.Install Java  
- repositoryが設定されているか確認 
  ```bash
  sudo dnf repolist
  ```
   ```bash
  sudo dnf list java-17-openjdk
  ```
- java 1.17のインストール
  ```bash
  sudo dnf install java-17-openjdk
  ```
  ```bash
  java -version
  ```
  
  
---
## 4.Install and configure Minecraft Forge
-  Forgeの最新バージョンを確認してDLする(e.g. 1.20.1-47.4.13)
 ```bash
  curl -s https://files.minecraftforge.net/net/minecraftforge/forge/maven-metadata.json | grep 1.20.1 
  ```
- インストールディレクトリを作成してインストーラーをDL 
 ```bash
  mkdir forge-server-1.20.1-47
  cd forge-server-1.20.1-47
  ```
  ```bash
  wget https://files.minecraftforge.net/maven/net/minecraftforge/forge/1.20.1-47.4.13/forge-1.20.1-47.4.13-installer.jar
  ```
  ```bash
  ls -lh forge-1.20.1-47.4.13-installer.jar
  ```
- インストーラーを実行 
  ```bash
  java -jar forge-1.20.1-47.4.13-installer.jar --installServer
  ```
- EURAファイルを生成
  ```bash
  ./run.sh
  ```
- EULAに同意する (生成されたeula.txtに記載のeura=faulseをtrueに変更)
  ```bash
  vi eula.txt
  ```

  ```bash
  $ cat eula.txt 
  eula=true
  ```
- argsの変更  
  ```bash
  vi user_jvm_args.txt
  ```
- 以下を設定
  ```
  -XX:+UnlockExperimentalVMOptions
  
  -Xms4G 
  -Xmx16G 
  
  -XX:+UseG1GC 
  -XX:MaxGCPauseMillis=200 
  -XX:+ParallelRefProcEnabled 
  
  -XX:G1NewSizePercent=20 
  -XX:G1MaxNewSizePercent=45 
  -XX:G1ReservePercent=20 
  
  -XX:G1HeapRegionSize=16M 
  
  -XX:+AlwaysPreTouch 
  
  -Dfile.encoding=UTF-8 
  ```

- 確認 
  ```bash
  $ cat user_jvm_args.txt
  ```
  

  
---
## 5.Configure systemd for minecraft
- 専用ユーザーを作成
 ```bash
sudo useradd -r -m -d /opt/minecraft -s /bin/bash minecraft 
```
- Forge ディレクトリを /opt/minecraft に移動
 ```bash
sudo mv ~/forge-server-1.20.1-47/* /opt/minecraft/
sudo chown -R minecraft:minecraft /opt/minecraft
```

- systemd ユニットファイルを作成
 ```bash
sudo vi /etc/systemd/system/minecraft.service
```
* 以下を記載
```
[Unit]
Description=Minecraft Forge Server
After=network.target

[Service]
Type=simple
User=minecraft
WorkingDirectory=/opt/minecraft

ExecStart=/bin/bash /opt/minecraft/run.sh nogui
ExecStop=/bin/bash -c 'echo "stop" | nc localhost 25565'
Restart=on-failure
RestartSec=10

TimeoutStopSec=60
KillMode=control-group

[Install]
WantedBy=multi-user.target
```

- systemdへの反映
```bash
sudo systemctl daemon-reload
```

- 自動起動設定
```bash
sudo systemctl enable minecraft
```
  
---
## 6.Start Minecraft server
- 起動
  ```bash
  sudo systemctl start minecraft 
  ```
- 確認
  ```bash
  sudo systemctl status minecraft
  ```
- 停止
```bash
  sudo systemctl stop minecraft 
```
- ログ確認
```bash
journalctl -u minecraft -f 
```
