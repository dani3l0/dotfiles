#!/bin/bash

# Max CPU Freq
freq=2700
for file in /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq; do echo -n $(($freq * 1000)) > $file; done
echo "CPU Max Frequency set to $freq"

# CPU Freq Power Policy
for policy in /sys/devices/system/cpu/cpufreq/policy*; do echo "balance_power" > "$policy/energy_performance_preference"; done
