# How to install mod files to Minecraft-Forge server on OCI 
Minecraft-Forge鯖にmodファイルを追加する方法  


## Requirements
- SSHクライアント (e.g.PowerShell)
- SFTPクライアント (e.g. WinSCP)
- modファイル(.jar)  


## Notes
- 初回:手順1 -> 手順2 -> 手順3 -> 手順4
- 2回目以降: 手順2 -> 手順3 -> 手順4 

---
## 1. Preparing SSH and SFTP
注: SSHとSFTPができればどのツールでもOK。ここではPowerShellとWinSCPの手順を記載  

### 1-1. SSHクライアントの起動
- Windowsで"PowerShell"を検索 > 起動
  
  <img width="783" height="776" alt="Screenshot 2025-12-26 143126" src="https://github.com/user-attachments/assets/5cd09015-982b-4bd0-8420-74498d2f2b94" /> 
  <img width="1105" height="620" alt="Screenshot 2025-12-26 143609" src="https://github.com/user-attachments/assets/ec0d13e7-8f71-4b55-992d-73b5fb278470" />

### 1-2. SFTPクライアントのインストールとマイクラ鯖への接続設定　
- サイトからWinSCPをダウンロードしインストール (https://winscp.net/eng/download.php)
- WinSCPの起動 

  <img width="776" height="777" alt="Screenshot 2025-12-26 144203" src="https://github.com/user-attachments/assets/644b33e9-cb2b-4cb0-84dc-fdebfadb6f32" />
  <img width="1073" height="689" alt="Screenshot 2025-12-26 144408" src="https://github.com/user-attachments/assets/66f1d233-1e32-47cb-99f5-a91b76036282" />
  
  



- SFTPの接続設定
  - File protocol: SFTP (変更なし)
  - HostName: マイクラ鯖のIP
  - Port: 22 (変更なし)
  - User name: opc
  - Password: 空欄のまま  
  
  <img width="641" height="418" alt="Screenshot 2025-12-26 151136" src="https://github.com/user-attachments/assets/3b28d8bb-f8bd-4388-ad20-b0b3f605c147" />  

- [Advanced...]をクリックして詳細画面を開く
  
  <img width="641" height="418" alt="Screenshot 2025-12-26 151136" src="https://github.com/user-attachments/assets/962828d9-086c-47b8-9608-40b64b779e40" /> 
  
- SSH > Authentication > Private Key file
  
  <img width="612" height="450" alt="Screenshot 2025-12-26 152136" src="https://github.com/user-attachments/assets/33bb7e63-fac6-4dac-86ba-72d4aa7e7777" /> 
   
- 自PCに保存した秘密鍵ファイルを選択 > [Open]
  
  <img width="832" height="370" alt="Screenshot 2025-12-26 152308" src="https://github.com/user-attachments/assets/1ea30c1e-036a-402a-8340-7e12a601935d" />
  
- .ppkフォーマット変換の確認のポップアップがでるので[OK]をクリック

  <img width="440" height="209" alt="Screenshot 2025-12-26 152637" src="https://github.com/user-attachments/assets/5415524e-dc82-4747-9ddb-0b36d3a474f7" />

  
- 変換したファイルを保存([Save]をクリック) > [OK]をクリック
  
  <img width="942" height="526" alt="Screenshot 2025-12-26 153154" src="https://github.com/user-attachments/assets/f8def370-e1d0-4ef5-8b61-e99b9f26371e" />
  <img width="569" height="136" alt="Screenshot 2025-12-26 153104" src="https://github.com/user-attachments/assets/f6532a93-c836-428b-be1a-ab8baf83087c" />  

  
- Private Key fileに.ppkファイルのパスが設定されたことを確認して[OK]をクリック
  
  <img width="617" height="457" alt="Screenshot 2025-12-26 153613" src="https://github.com/user-attachments/assets/a14b021d-1eda-448f-867d-8ac3483ced48" />  

  
- 左ペインの[New Site]を右クリック > [Save As]
  
  <img width="643" height="421" alt="Screenshot 2025-12-26 175558" src="https://github.com/user-attachments/assets/2163c5c9-806c-426d-b528-77b02573606a" /> 

- [Site name]に適当な名前を入力 > [OK]
  
  <img width="365" height="214" alt="Screenshot 2025-12-26 175830" src="https://github.com/user-attachments/assets/43e359e8-3d0b-4016-ba99-86c2512221d7" />  

- 左ペインに保存したマイクラ鯖のログイン情報が表示される
  
  <img width="642" height="421" alt="Screenshot 2025-12-26 175844" src="https://github.com/user-attachments/assets/63074aad-992e-4108-998d-13073155e3c0" />  



  
---
## 2. Upload mod files to Minecraft Server 
- WinSCPを起動 (接続画面が表示されない場合は[New Tab]をクリックすると接続画面が表示される
  
  <img width="1065" height="681" alt="Screenshot 2025-12-26 231836" src="https://github.com/user-attachments/assets/666fb74f-91b9-414f-97a5-2aa6dc516c57" /> 
    
- マイクラ鯖へSFTPでログインする。マイクラ鯖の接続情報を選択して[Login]をクリック (Cashのポップアップが表示されたら[Accept]する )
  
  <img width="473" height="374" alt="Screenshot 2025-12-26 232958" src="https://github.com/user-attachments/assets/1ec05246-e88a-40a2-99eb-ae58001cbc81" />

- マイクラ鯖に接続される

  <img width="1065" height="683" alt="Screenshot 2025-12-27 004630" src="https://github.com/user-attachments/assets/6d2ee927-726d-4fef-a41a-e5cbe46462f2" />
  
- 左側:自PCのフォルダ構成が表示される -> マイクラ鯖に追加するmodが格納されているフォルダへ移動する
  右側:マイクラ鯖のフォルダ構成が表示 -> modsフォルダへ移動(/home/opc/mods)

  <img width="1072" height="693" alt="Screenshot 2025-12-27 002402" src="https://github.com/user-attachments/assets/5604326e-e38e-45ee-a5f2-513900efc51b" />
  
- 追加したいmodファイルを選択し、左側(自PC)から右側(マイクラ鯖)にファイルをドラッグする (ポップアップが表示されたらOKをクリック)
  
  <img width="1070" height="684" alt="Screenshot 2025-12-27 005610" src="https://github.com/user-attachments/assets/33173735-d966-430b-90d3-6e271dc23683" />
  <img width="403" height="230" alt="Screenshot 2025-12-27 011738" src="https://github.com/user-attachments/assets/b1e3295d-99b8-46b3-909d-3fc39269746c" />
  
- マイクラ鯖へのSFTPセッションを切断(ツールを閉じるか、タブを右クリック > [Disconnect])
  
  <img width="1060" height="641" alt="Screenshot 2025-12-27 011942" src="https://github.com/user-attachments/assets/17a5c28c-a688-4954-9b58-3d8818e80d6a" />
  

---
## 3. Install mod files
- PowerShellを起動
  
- マイクラ鯖にSSHでログイン (初回ログイン時は接続確認のメッセージが出るはずなので、その場合はyesと打つ) 
  ```bash
  ssh -i ~/.ssh/ssh-key-oci.key opc@[マイクラ鯖のIPアドレス]
  ```
  
  <img width="1105" height="615" alt="Screenshot 2025-12-27 013622" src="https://github.com/user-attachments/assets/05d14f10-70b2-4173-95ee-170c927ceb4e" /> 

- modsディレクトリに移動
  ```bash
  cd mods
  ```

  <img width="728" height="64" alt="Screenshot 2025-12-27 013943" src="https://github.com/user-attachments/assets/576e7280-e45c-4910-a1f2-3eae147efe04" /> 
  
- modファイルをマイクラのインストールフォルダにコピー
    - modファイルを個別にコピーする場合
      ```bash
      sudo cp -f [modファイル名] /opt/minecraft/mods
      ```

      <img width="805" height="51" alt="Screenshot 2025-12-27 014412" src="https://github.com/user-attachments/assets/f5e2ef54-e84d-4386-8cfe-0ff0c56efcb1" /> 

    - すべてのファイルをコピーする場合
      ```bash
      sudo cp -f *.jar /opt/minecraft/mods
      ```

      <img width="654" height="82" alt="Screenshot 2025-12-27 014228" src="https://github.com/user-attachments/assets/abcf5d03-5e24-406a-811c-f4e3879da892" /> 

- modファイルの所有者を変更
  ```bash
  sudo chown -R minecraft:minecraft /opt/minecraft/mods
  ```

  <img width="699" height="63" alt="Screenshot 2025-12-27 015010" src="https://github.com/user-attachments/assets/0b1a73c6-6312-4d01-9038-6be905c983ec" />


---
## 4. Restart Minecraft Server
- Minecraftのステータス確認
  ```bash
  sudo systemctl status minecraft
  ```
  
  <img width="1098" height="217" alt="Screenshot 2025-12-27 020244" src="https://github.com/user-attachments/assets/25a7286f-183e-496a-b53c-bf6cab01c53f" />
    

- Minecraftの再起動
  ```bash
  sudo systemctl restart minecraft
  sudo systemctl status minecraft
  ```

   <img width="1098" height="299" alt="Screenshot 2025-12-27 020540" src="https://github.com/user-attachments/assets/ee38b5f4-c5ca-47d4-be88-1120407da204" />
    
