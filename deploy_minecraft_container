# How to build Minecraft Container and deploy it 
バニラなMinecraftコンテナを作成し、OCI(Oracle Linux9)にデプロイする手順

---
## Requirements
- SSHクライアント(e.g.PowerShell)
- Java 1.25
- Minecraft 1.69.0 

---
## 1.Create a image with Minecraft server.jar as server1  
- ディレクトリを作る
 <img width="160" height="171" alt="image" src="https://github.com/user-attachments/assets/944febf3-d8ee-4609-ae24-aaca512aad26" />

   ```
   mkdir -p ~/minecraft/image
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
  cd ~/minecraft/image
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

## 2.Create EULA files
  - EULAファイルを作成
  ```
  echo "eula=true" > ~/minecraft/server1/eula.txt
  echo "eula=true" > ~/minecraft/server2/eula.txt 
  ```

## 3.Run Minecraft#1
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

## 4.Change Configuration
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
