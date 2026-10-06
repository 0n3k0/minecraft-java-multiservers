# How to deploy Minecraft multiple servers on OCI 
OCIの無料枠を利用して複数のMinecraft鯖(コンテナ)をたてる手順

---
## Requirements
- Oracle Cloud Infrastracture(OCI)のFree Tierアカウント(https://www.oracle.com/jp/cloud/free/) 
  - Tokyo Regionはリソースに空きがないらしいのでOsakaを選択した方がいい
  - Free TierのままだとOsakaでもリソースがないというapiエラーになる。有料サブスクリプションにアップグレードしたら解決 (無料の範囲で使えば課金されない)
  - 無料枠でおさめるならARM 4ocpu, 24GBRAMのLinuxインスタンス1個 <- 無料枠が小さくなったので注意
- SSHクライアント(e.g.PowerShell)
- Java 1.17
- Minecraft-forge 1.20.1 

    
3,000 OCPU hours and 18,000 GB hours per month > 4OCPU & 24GB for a ARM VM per 31 days  
![Screenshot_25-12-2025_143824_www oracle com](https://github.com/user-attachments/assets/1f414f1f-7bd1-49dd-9450-87becf50aded) 
  
  <img width="361" height="411" alt="image" src="https://github.com/user-attachments/assets/1a667af5-7aaa-4ab9-a66e-988abd27955d" />



---
## 1. Deployment & Configuration OCI env.   
### 1-1.Create compartment
- サブコンパートメントの作成(作らなくてもいいけど作った方がいい) 

<img width="1307" height="466" alt="Screenshot 2025-12-23 at 15 16 37" src="https://github.com/user-attachments/assets/e3c254a7-a9bc-4b88-a393-e6db92be87b9" /> 
<img width="1288" height="529" alt="Screenshot 2025-12-23 at 15 19 59" src="https://github.com/user-attachments/assets/cdef06d4-1c95-43dd-a2ef-35289f172a1e" />  
  

### 1-2.Create Network
- Public networkとIGWを作成
- private networkは無し 
- インスタンスのvnicにグローバルipを設定しIGWから直接ルーティングさせる  
![Screenshot_22-12-2025_231321_cloud oracle com](https://github.com/user-attachments/assets/f9d0071b-2644-4b38-b63e-e769521bf6b2) 
![Screenshot_22-12-2025_231356_cloud oracle com](https://github.com/user-attachments/assets/90f010fa-0498-4992-bd9a-d18f2e7da5bd) 
![Screenshot_22-12-2025_231356_cloud oracle com](https://github.com/user-attachments/assets/b0871a30-b50f-4c47-ab39-82e79eed0de3) 
![Screenshot_22-12-2025_231415_cloud oracle com](https://github.com/user-attachments/assets/56f2bd71-b86d-458f-a90b-a9eeaf1459ac) 
![Screenshot_22-12-2025_23150_cloud oracle com](https://github.com/user-attachments/assets/f3d9142c-f9b3-4030-b46a-97f4c5f21286)
![Screenshot_22-12-2025_231436_cloud oracle com](https://github.com/user-attachments/assets/75b5b9f2-a115-4601-8746-a3729b259ae9)  
![Screenshot_22-12-2025_232231_cloud oracle com](https://github.com/user-attachments/assets/f5da4fa2-dfe9-4140-b7c3-bb53252701db) 
![Screenshot_22-12-2025_232249_cloud oracle com](https://github.com/user-attachments/assets/2a7e6964-49ac-4513-887e-e2aeddb284e6) 
![Screenshot_22-12-2025_23232_cloud oracle com](https://github.com/user-attachments/assets/8a25925e-49b5-4c3a-a35e-90469509a6cd) 
![Screenshot_22-12-2025_232340_cloud oracle com](https://github.com/user-attachments/assets/9f4193f3-fda4-4a38-9813-4b1a2457cbcf) 
![Screenshot_22-12-2025_232359_cloud oracle com](https://github.com/user-attachments/assets/78a17ce5-334a-4ae8-a683-b6b348f07da5) 


### 1-3.Deploy instance
インスタンス 
- 名前: 任意 (minecraft-forge-1.20.1) 
- コンパートメント: デフォルト 
- 配置: AD1 (OENr:AP-OSAKA-1-AD-1) 
- 拡張オプション: 変更なし 
- シェイプ: Ampere (ARM), VM.Standard.A1.Flex 
- イメージ: 任意 (OracleLinux or Ubuntu or CentOS) 
- OCPU: 任意, 4 
- メモリ: 任意, 24GB  

![Screenshot_22-12-2025_225715_cloud oracle com](https://github.com/user-attachments/assets/39329e6a-d400-43d5-84f1-964f28e04584)


ネットワーク

ネットワーキング
- vnic: 任意 (vnic01) 
- 新規仮想クラウドネットワーク 
- 名前: 任意 (vcn-network01)  

サブネット
- 名前: 任意 (subnet-network01)
- CIDR: 10.0.0.0/24  

SSHキーの追加
- キー・ペアを自動で生成
- 秘密鍵と公開鍵をダウンロードしておく  

![Screenshot_22-12-2025_23140_cloud oracle com](https://github.com/user-attachments/assets/d73794ba-b57a-45b0-96e0-8f8ada0e6d11)
![Screenshot_22-12-2025_23230_cloud oracle com](https://github.com/user-attachments/assets/0e2a5621-9259-48df-8eca-c7837575c7eb)

  
ストレージ
- ブートボリューム: デフォルト サイズは100GB (200GBまで)
- ブロックボリューム: ひとまずなし  

![Screenshot_22-12-2025_23746_cloud oracle com](https://github.com/user-attachments/assets/127e2a12-a974-470c-8d53-2b06ed6d13d1)
![Screenshot_22-12-2025_23918_cloud oracle com](https://github.com/user-attachments/assets/9ac7438d-cec5-406f-8bca-7b8d03c48618)


### 1-4.Check to access the instance by ssh 

- 開発者シェル > Cloud Shell または PowerShellnなどのSSHクライアントを起動  
- private keyファイルをクライアントに設定(Cloud Shellの場合は歯車からkeyファイルをアップロード、PowerShellの場合は~/.ssh/配下に配置)
- keyファイルのパーミッション変更
```bash
 chmod 600 [ssh-key file] 
```
- ssh接続確認(Oracle Linuxの場合はユーザー名はopc) 
 ```bash
ssh -i ~/[sssh key] opc@xx.xxx.xxx.xxx 
```
  
---
## 2.Configure security rule for minecraft
- Ingress ruleにマイクラ用のポートを追加 (vpn > subnet > Security rules)
  ![Screenshot_25-12-2025_132350_cloud oracle com](https://github.com/user-attachments/assets/10901b49-4ef2-452f-a7ee-2dcb43a7c172)
  <img width="1256" height="755" alt="image" src="https://github.com/user-attachments/assets/9589662c-7378-4fe1-a34e-c71fbb28a259" />

  
- Linux側もポートの穴あけ
 ```bash
 sudo firewall-cmd --add-port=25565/tcp --permanent
 sudo firewall-cmd --add-port=25566/tcp --permanent 
 sudo firewall-cmd --reload
```
  
---
## 3.Install Podman  
- podmanをインストール 
   ```bash
  sudo dnf install -y podman 
  ```
- EPEL repoを有効にする 
  ```bash
  sudo dnf install -y oracle-epel-release-el9 
  sudo dnf config-manager --enable ol9_developer_EPEL
  sudo dnf install -y oracle-java-jdk-release-el*
  dnf repolist 
  ```
- Composeのインストール  
  ```bash
  sudo dnf install -y podman-compose 
  ```
  ```bash
  podman --version
  podman-compose --version 
  ```

---
## 4.Create a image with Minecraft server.jar as server1  
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






