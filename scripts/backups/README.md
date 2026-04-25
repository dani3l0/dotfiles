# backups

Simple yet reliable backup script written in Python

doing snapshots so storage is not wasted :P

**REQUIREMENTS**

- **vanilla python3**; this has no external module requirements

- **rsync**; needs to be installed for doing actual backups

- **hdparm**; for spinning down disks (mine don't have APM)

- **curl**; for sending notifications to ntfy

- **btrfsprogs**; for filesystem support

- **💾 2x disks formatted as BTRFS RAID1** - for primary backups

- **💿 1x external disk formatted as BTRFS as well** - for off-site backups, best to be USB one

- **📬 ntfy server** - as the notifier

------

config is inside `backups.py` because i'm too lazy to do the proper structure

