#!/usr/bin/env bash
set -euo pipefail

# Check the current CPU temperature and reboot the system if it exceed desired value.
# Useful for Raspberry PI and similar, when it goes to infinite loop.
# Reboot events are logged to syslog. Inspect with: journalctl -t temp-monitor
#
# Must run as root (reboot requires it). Install in root's crontab:
#   sudo crontab -e

MAX_TEMP="${MAX_TEMP:-75}"
LOG_TAG="temp-monitor"

if [ "$(id -u)" -ne 0 ]; then
    echo "Must run as root (reboot requires it)." >&2
    exit 1
fi

if ! command -v vcgencmd >/dev/null 2>&1; then
    echo "vcgencmd not found — this script is intended for Raspberry Pi." >&2
    exit 1
fi

# vcgencmd prints `temp=49.8'C`; strip everything but digits and the dot.
temp_c=$(vcgencmd measure_temp | awk '{gsub(/[^0-9.]/, ""); print}')

if awk -v t="$temp_c" -v max="$MAX_TEMP" 'BEGIN { exit !(t > max) }'; then
    logger -t "$LOG_TAG" "Temperature ${temp_c}°C exceeded ${MAX_TEMP}°C — rebooting"
    reboot
fi
