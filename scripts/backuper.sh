#!/bin/bash

########## How to run ##########
# source /path/to/backuper.sh
# make_full_backup - does a full backup, auto mounts, unmounts and spindowns the disks
# backuper - runs an infinite loop which checks time and does backups automagically, useful with systemD
################################

############################## CONFIG ##############################

BACKUP_AT="17:00"											# When to do daily backups
BACKUP_TARGET_UUID="some-uuid-for-brtfs"					# UUID of target BTRFS disk (in RAID0 configuration)
BACKUP_TARGET_PATH="/storage/backup"						# Where to mount the target disk
BACKUP_DIR="Backups"										# Target folder name
NTFY_URL="http://127.0.0.1:8080/MyTopic"					# Where to post ntfy notifications
SPINDOWN_DEVICES="/dev/sdx /dev/sdy /dev/sdz"				# Force spindown backup disks (useful when APM is unavailable)

####################################################################

# Logger
function notify() {
	# $1: Emoji tag | https://docs.ntfy.sh/emojis/
	# $2: Title
	# $3: Message

	# send message via ntfy
	curl -H "Tags: $1" -H "Title: $2" -d "$3" $NTFY_URL

	# And do an echo
	echo $2
	echo $3
}

function backup_storage() {
	# Aliases for variables
	STORAGE_PATH=$1
	BACKUP_TARGET_PATH=$2

	# Magic
	echo "Backing up '$STORAGE_PATH' ..."
	mkdir -p "$BACKUP_TARGET_PATH/$BACKUP_DIR/$STORAGE_PATH"
	rsync -aq --delete "$STORAGE_PATH/" "$BACKUP_TARGET_PATH/$BACKUP_DIR/$STORAGE_PATH/"
	error=$?
	if [[ $error -ne 0 ]]; then
		notify "warning" "Backup failed!" "Rsync job for $STORAGE_PATH returned with error $error."
	else
		notify "white_check_mark" "Backup successful" "Rsync job for $STORAGE_PATH completed without errors."
	fi
}

function spindown() {
	hdparm -Y $SPINDOWN_DEVICES
}

function make_full_backup() {
	# Mount backup partition
	mount "/dev/disk/by-uuid/$BACKUP_TARGET_UUID" "$BACKUP_TARGET_PATH"
	sleep 30

	# Backup data, can be edited
	backup_storage	"/home"			$BACKUP_TARGET_PATH

	# Unmount & spindown HDDs
	sleep 90
	umount $BACKUP_TARGET_PATH
	sleep 30
	spindown
}


function backuper() {
	sleep 120
	spindown

	BACKUP_DONE_TODAY=1

	while true
	do
		now=$(date +%H:%M)

		# If it is later than BACKUP_AT and backup was not made today, do it
		if [[ "$now" > "$BACKUP_AT" ]] && [[ $BACKUP_DONE_TODAY -eq 0 ]]; then
			BACKUP_DONE_TODAY=1
			make_full_backup
		fi

		# If it is earlier than BACKUP_AT, let's assume there was no backup today
		if [[ "$now" < "$BACKUP_AT" ]]; then
			BACKUP_DONE_TODAY=0
		fi

		sleep 900
	done
}

