import os
import datetime
import time

# Setup
UID = 64055
GID = 1000
PERMS = 0o660
PATH = "/srv/VMs"

# Main l00p
while True:
	time.sleep(15)
	try:
		d = datetime.datetime.now()
		if d.minute not in [0, 15, 30, 45]:
			continue
		for filename in os.listdir(PATH):
			f = os.path.join(PATH, filename)
			st = os.stat(f)
			if not ((st.st_mode & 0o660) == 0o660) or st.st_uid != UID or st.st_gid != GID:
				timestamp = d.strftime("[%H:%M:%S %d-%b-%y]")
				print(f"{timestamp} Changing perms for {f}")
				os.chown(f, UID, GID)
				os.chmod(f, PERMS)
	except:
		pass
