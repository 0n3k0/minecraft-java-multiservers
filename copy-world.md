# How to copy Minecraft World data
## Backup of the source data 
- need to backup files
  - world/
  - mods/
  - config/
  - server.properties

- stop mainecraft server

- full-backup
  ```bash
  sudo tar czvf backup_before_migration_$(date +%Y%m%d).tar.gz \
  /opt/minecraft/world \
  /opt/minecraft/mods \
  /opt/minecraft/config \
  /opt/minecraft/server.properties
  ```

- minimum-backup
  ```bash
  sudo tar czvf world_backup_$(date +%Y%m%d).tar.gz \
  /opt/minecraft/world
  ```

- copy world data
  ```bash
  sudo cp -R world/ /opt/minecraft/.
  sudo chown -R minecraft:minecraft /opt/minecraft/world
  sudo cp -r mods config /opt/minecraft/
  sudo chown -R minecraft:minecraft /opt/minecraft/mods
  sudo chown -R minecraft:minecraft /opt/minecraft/config
  sudo cp server.properties /opt/minecraft/
  sudo chown minecraft:minecraft /opt/minecraft/server.properties
  ```

- start mainecraft server
