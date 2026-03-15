#!/usr/bin/env bash
set -euo pipefail

############################################################
# Readme
############################################################
# The script to sync source folder to the destination one, using rclone command.
# Consider adding variables: REMOVE_SOURCE_FILES

############################################################
# Params
############################################################
SOURCE="<SOURCE>"
DESTINATION="<DESTINATION>"
HI_SPEED_LIMIT="50M"
LOW_SPEED_LIMIT="1M"
LOG_FILE="/home/marko/sync_log.out"

############################################################

# Check if already running
RCLONE_OCCURRENCES=$(pgrep -c rclone || true)
if [ "$RCLONE_OCCURRENCES" -gt 1 ]
then
    echo "Sync script is already running. Skipping."
    exit 1
fi

# Calculate the speed limit based on the current time
TIME_HOURS=$(date +"%H")
if [ "${TIME_HOURS}" -ge 23 ] || [ "${TIME_HOURS}" -lt 6 ]
then SPEED_LIMIT=${HI_SPEED_LIMIT}
else SPEED_LIMIT=${LOW_SPEED_LIMIT}
fi

# Run the command
rclone copy "$SOURCE" "$DESTINATION" \
  -P --transfers=1 --checkers=1 --multi-thread-streams=0 \
  --bwlimit="$SPEED_LIMIT" \
  --max-age 2d \
  --exclude '*.part' \
  2>&1 | tee -a "$LOG_FILE"

exit 0
