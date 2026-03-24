#!/usr/bin/env bash
set -euo pipefail

############################################################
# Readme
############################################################
# The script to sync source folder to the destination one, using rclone command.
# Consider adding variables: REMOVE_SOURCE_FILES

############################################################
# Config
############################################################
ENV_FILE="$(dirname "$0")/.env"

if [ ! -f "${ENV_FILE}" ]; then
    echo "Missing config file: ${ENV_FILE}" >&2
    exit 1
fi

set -a
# shellcheck source=/dev/null
. "${ENV_FILE}"
set +a

: "${SOURCE:?SOURCE must be set in ${ENV_FILE}}"
: "${DESTINATION:?DESTINATION must be set in ${ENV_FILE}}"

HI_SPEED_LIMIT="${HI_SPEED_LIMIT:-50M}"
LOW_SPEED_LIMIT="${LOW_SPEED_LIMIT:-1M}"
LOG_FILE="${LOG_FILE:-sync_log.out}"
MAX_AGE="${MAX_AGE:-2d}"
EXCLUDE="${EXCLUDE:-*.part}"

if [ "$#" -ge 1 ]; then
    MAX_AGE="$1"
fi

if [ "$#" -ge 2 ]; then
    SOURCE="$2"
fi

############################################################

# Check if already running
LOCK_FILE="/tmp/sync_script.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
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
  --max-age "$MAX_AGE" \
  --exclude "$EXCLUDE" \
  2>&1 | tee -a "$LOG_FILE"

exit 0
