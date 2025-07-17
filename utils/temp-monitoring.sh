#!/bin/bash

# Check the current CPU temperature and reboot the system if it exceed desired value.
# Useful for Raspberry PI and similar, when it goes to infinite loop.

MAX_TEMP=750  # 75.0°C × 10

temp=$(vcgencmd measure_temp | grep -oP '\d+\.\d+' | awk '{print $1 * 10}' | cut -d'.' -f1)
if [ "$temp" -gt "$MAX_TEMP" ]; then
  echo "Temperature limit exceeded! Rebooting..."
  sudo reboot
fi
