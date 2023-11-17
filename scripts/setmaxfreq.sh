#!/bin/bash

# Sets max CPU frequency to save power
# Usage:
# -> Just run the script and it will ask for target frequency
# -> Provide an integer as first parameter, value in MHz

if [ -z ${1+x} ]; then
	echo -n "Set target CPU frequency in MHz: "
	read freq

else
	freq=$1
fi

for file in /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq; do echo -n $(($freq * 1000)) > $file; done
echo "CPU Max Frequency set to $freq"
