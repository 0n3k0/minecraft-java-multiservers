# How to build Minecraft forge container and deploy it 
Minecraft forge鯖(コンテナ)をたてる手順

---
## Requirements
- SSHクライアント(e.g.PowerShell)
- Java 1.17
- Minecraft-forge 1.20.1 


---
## 1.Get Oracle Linux 9 image  
- Oracle Linux 9イメージをダウンロード
  ```
  podman pull container-registry.oracle.com/os/oraclelinux:9 
  ```
- イメージの確認
   ```
   podman image inspect \
   container-registry.oracle.com/os/oraclelinux:9 \
   --format '{{.Architecture}}'
   ```  

- コンテナを起動 
  ```
  podman run -d \
  --name ol9-test \
  container-registry.oracle.com/os/oraclelinux:9 \
  sleep infinity 
  ```
  
- 確認
  ```
  podman ps
  ```

- コンテナのシェルに入る
  ```
  podman exec -it ol9-test /bin/bash
  ```
  ```
  cat /etc/oracle-release
  uname -m
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
