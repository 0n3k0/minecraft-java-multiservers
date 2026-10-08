# How to add/remove user to/from whitelist 
RCONを使ってホワイトリストに接続を許可するユーザーを登録/削除する方法

---
## Requirements
- RCON

---
## 1. Add user to whitelist  
  - ホワイトリストへの追加 (Minecraft Java EditionのProfile Name)
  ```
  mcrcon -H 127.0.0.1 -P 25575 -p 'RCONパスワード' "whitelist add Minecraftユーザー名"
  ```
  - 確認
  ```
  mcrcon -H 127.0.0.1 -P 25575 -p 'RCONパスワード' "whitelist list"
  ```

## 2. Remove user from whitelist
  - ホワイトリストからの削除 (Minecraft Java EditionのProfile Name)
  ```
  mcrcon -H 127.0.0.1 -P 25575 -p 'RCONパスワード' "whitelist remove Minecraftユーザー名"
  ```
  - 確認
  ```
  mcrcon -H 127.0.0.1 -P 25575 -p 'RCONパスワード' "whitelist list"
  ```
