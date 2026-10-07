# How to build Minecraft forge container and deploy it 
Minecraft forge鯖(コンテナ)をたてる手順
<br>
<br>

## Requirements
- SSHクライアント(e.g.PowerShell)
- Java 1.17
- Minecraft-forge 1.20.1
- 注: バックアップデータを利用
<br>
<br>

## Table of Contents
[1. Create a image](#1-Create-a-image)  
[2. Run the image](#2-Run-the-image)  
[3. Restore backup data](#3-Restore-backup-data)  
[4. Install Mod files](#4-Install-Mod-files)  
[5. Configure SELinux](#5-Configure-SELinux)  
[6. Run Minecraft-forge server](#6-Run-Minecraft-forge-server)  
[7. Configure systemd](#7-Configure-systemd)  



<br>
<br>

## 1. Create a image  
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
<br>
<br>


## 2. Run the image  
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
<br>
<br>

## 3. Restore backup data  
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
<br>
<br>

## 4. Install Mod files  
  - modファイルをコピー
  ```
  sudo cp /home/opc/mods/* ~/minecraft/server2/mods
  ```
<br>
<br>


## 5. Configure SELinux  
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
  - 注: パーミッションの問題で起動できなかったのでいろいろトラシューした残骸コマンド
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

<br>
<br>

## 6. Run Minecraft-forge server  
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

<br>
<br>

## 7. Configure systemd  
  - opcをログアウトしてもuser systemdを維持するように設定
  ```
  sudo loginctl enable-linger opc
  ```
  - 確認（Linger=yesならOK)
  ```
  loginctl show-user opc -p Linger
  ```



