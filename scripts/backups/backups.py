import subprocess
import time, os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

########################################### CONFIG ###########################################

BACKUP_AT = "17:00"														# backup at HH:MM
BACKUP_DAYS = 3															# backup each n days
PURGE_DAYS = 60															# the oldest snapshot to keep
BACKUP_TARGET_UUID = "a1b2c3d4-e5f6-7890-1234-567890abcdef"				# UUID of RAID BTRFS filesystem
BACKUP_TARGET_PATH = "/mnt/backups"										# Where RAID BTRFS partition should be mounted
BACKUP_DIR = "Backups"													# btrfs subvolume
NTFY_URL = "http://127.0.0.1:8080/ServerAlerts_up4e9hpR"				# ntfy URL
SPINDOWN_DEVICES = ["/dev/disk/by-partuuid/a1b2c3d4-e5f6-7890-1234-567890abcdef",	# Paths to disks to spin down
			"/dev/disk/by-partuuid/1a2b3c4d-5e6f-7890-abc1-234567890fed"]			# by using hdparm -Y
OFFSITE_UUID = "1a2b3c4d-5e6f-7890-abc1-234567890fed"			# Offsite backup partition UUID
OFFSITE_PATH = "/mnt/offsiteBackups"							# Where offsite backup partition should be mounted
OFFSITE_SNAPSHOTS_COUNT = 10									# Max number of offsite snapshots
STORAGES = ["/home", "/storage/files"]							# Directories to be backed up
IGNORES = ["*/.local/share/containers", "*/.cache"]				# Ignore those directories in rsync

##############################################################################################

# PUSH Notifications & Logger
def notify(title, message):
	subprocess.run(["curl", "-H", f"Tags: floppy_disk", "-H", f"Title: {title}", "-d", message, NTFY_URL])
	log(f"{title} | {message}")


# Make a backup of one
def backup_storage(storage_path, backup_target_path=BACKUP_TARGET_PATH):
	log(f"Backing up '{storage_path}' ...")
	backup_dir = os.path.join(backup_target_path, BACKUP_DIR)
	if not os.path.exists(backup_dir):
		os.makedirs(backup_dir)

	# Prepare rsync command
	rsync_cmd = ["rsync", "-aq", "--delete"]
	for folder in IGNORES:
		rsync_cmd.extend(["--exclude", folder])
	rsync_cmd.extend([storage_path, backup_dir])

	# Execute rsync and collect errors
	r = subprocess.run(rsync_cmd, capture_output=True, text=True)
	if r.returncode != 0:
		stderr = "\n"
		for line in r.stderr.split("\n")[-25:]:
			stderr += line
		notify("Backup failed!", f"Rsync job for {storage_path} returned with error {r.returncode}{stderr}")
	else:
		notify("Backup successful!", f"Rsync job for {storage_path} completed without errors.")


# Spindown all drives
def spindown():
	for device in SPINDOWN_DEVICES:
		log(f"Spinning down {device}...")
		subprocess.run(["hdparm", "-Y", device])


# Make full backup
def make_full_backup():
	# Mount
	log("Mounting backup drive...")
	subprocess.run(["mount", f"/dev/disk/by-uuid/{BACKUP_TARGET_UUID}", BACKUP_TARGET_PATH])
	time.sleep(30)

	# Check if the target directory exists, create it if not
	backup_dir = os.path.join(BACKUP_TARGET_PATH, BACKUP_DIR)
	if not os.path.exists(backup_dir):
		os.makedirs(backup_dir)

	# Backup data
	for target in STORAGES:
		backup_storage(target)

	# Make snapshot, delete old ones
	time.sleep(10)
	snapshot_name = gen_snapshot_name()
	make_btrfs_snapshot(backup_dir, snapshot_name)
	find_snapshots_older_than(PURGE_DAYS)

	# Unmount & spindown HDDs
	time.sleep(90)
	log("Unmounting backup drive...")
	subprocess.run(["umount", BACKUP_TARGET_PATH])
	time.sleep(30)
	spindown()


# Make offsite backup
def make_offsite_backup():
	log("Mounting offsite backup drive...")
	subprocess.run(["mount", f"/dev/disk/by-uuid/{OFFSITE_UUID}", OFFSITE_PATH])
	notify("Offsite backup", "An external disk for off-site backups has been detected. Backup process will begin shortly.")
	time.sleep(30)
	if not os.path.islink(f"/dev/disk/by-uuid/{OFFSITE_UUID}"):
		notify("Offsite backup", "Aborted. Disk had been turned off.")
		return

	# Check if the target directory exists, create it if not
	backup_dir = os.path.join(OFFSITE_PATH, BACKUP_DIR)
	if not os.path.exists(backup_dir):
		os.makedirs(backup_dir)

	# Backup data
	for target in STORAGES:
		backup_storage(target, backup_target_path=OFFSITE_PATH)

	# Make snapshot, delete olders
	remove_offsite_snapshots()
	snapshot_name = gen_snapshot_name()
	make_btrfs_snapshot(backup_dir, snapshot_name, OFFSITE_PATH)

	# Unmount & Spindown
	time.sleep(60)
	subprocess.run(["umount", OFFSITE_PATH])
	time.sleep(30)
	subprocess.run(["hdparm", "-Y", f"/dev/disk/by-uuid/{OFFSITE_UUID}"])


def make_btrfs_snapshot(path, snapshot_name, target=BACKUP_TARGET_PATH):
	log("Making snapshot {snapshot_name}...")
	subprocess.run(["btrfs", "subvolume", "snapshot", "-r", path, f"{target}/{snapshot_name}"])

def gen_snapshot_name():
	return datetime.now().strftime("%Y%m%d-%H%M%S")

def remove_btrfs_snapshot(snapshot_name):
	log("Removing snapshot {snapshot_name}...")
	subprocess.run(["btrfs", "subvolume", "delete", f"{BACKUP_TARGET_PATH}/{snapshot_name}"])

def remove_offsite_snapshots():
	snaps = subprocess.run(["btrfs", "subvolume", "list", OFFSITE_PATH], capture_output=True, text=True, check=True).stdout.splitlines()
	for snap in snaps[:-OFFSITE_SNAPSHOTS_COUNT]:
		log(f"Removing offsite snapshot {snap} ...")
		subprocess.run(["btrfs", "subvolume", "delete", f"{OFFSITE_PATH}/{snapshot_name}"])

def snapshot_exists(snapshot_name):
	snapshot_path = os.path.join(BACKUP_TARGET_PATH, snapshot_name)
	return os.path.exists(snapshot_path)

def find_snapshots_older_than(days):
	oldest_date = datetime.now() - timedelta(days=days)
	snapshots = subprocess.run(["btrfs", "subvolume", "list", BACKUP_TARGET_PATH], capture_output=True, text=True, check=True).stdout.splitlines()
	for snapshot in snapshots:
		try:
			snapshot_info = snapshot.split()
			if len(snapshot_info) >= 8:
				date_string = snapshot_info[8]
				snapshot_date = datetime.strptime(date_string, "%Y%m%d-%H%M%S")
				if snapshot_date < oldest_date:
					log(f"Found old snapshot to be removed: {date_string}")
					remove_btrfs_snapshot(snapshot_info[8])
		except Exception as e:
			log(f"Error occurred while managing old snapshots: {e}")


def timestamp():
	current_time = datetime.now()
	return current_time.strftime("%d-%m-%Y %H:%M:%S")

def log(text):
	return print(f"[{timestamp()}] {text}")


def is_backup_day():
	current_date = datetime.now()
	day_of_year = current_date.timetuple().tm_yday
	return not day_of_year % BACKUP_DAYS

# Main loop
def backuper():
	log("Started")
	time.sleep(120)
	spindown()
	BACKUP_DONE_TODAY = True

	try:
		while True:
			now = time.strftime("%H:%M")

			# If it is later than BACKUP_AT and backup was not made today, do it
			if is_backup_day() and now >= BACKUP_AT and not BACKUP_DONE_TODAY:
				log("Doing full backup...")
				BACKUP_DONE_TODAY = True
				make_full_backup()
				log("Full backup done!")

			# If it is earlier than BACKUP_AT, let's assume there was no backup today
			if now < BACKUP_AT:
				BACKUP_DONE_TODAY = False

			# Check if offsite backup disk appeared
			if os.path.islink(f"/dev/disk/by-uuid/{OFFSITE_UUID}"):
				log("Doing offsite backup...")
				make_offsite_backup()
				log("Offsite backup done! You can now detach your disk.")
				while os.path.islink(f"/dev/disk/by-uuid/{OFFSITE_UUID}"):
					time.sleep(5)

			time.sleep(30)

	except Exception as e:
		notify("Backup service crashed!", f"Process exited with exception '{e}'.\nService needs to be restarted manually.")


if __name__ == "__main__":
	backuper()
