#!/usr/bin/env bash
set -euo pipefail

############################################################
# Usage
############################################################
# Sync SOURCE to DESTINATION via rclone, with time-of-day bandwidth limits.
#
#   sync.sh [--max-age VALUE] [--source PATH]
#
# Flags (both optional, override the corresponding value from .env):
#   --max-age VALUE   rclone --max-age, e.g. "2d", "12h" (default from .env, then "2d")
#   --source PATH     rclone source path; useful for ad-hoc one-off syncs
#
# Examples:
#   sync.sh                                  # use everything from .env
#   sync.sh --max-age 12h                    # tighter window, .env source
#   sync.sh --source /mnt/usb/photos         # ad-hoc source, .env max-age
#   sync.sh --max-age 7d --source /mnt/usb/photos
#
# Config is loaded from .env next to this script. See .env.example.
############################################################

############################################################
# Config
############################################################
# Resolve symlinks so a `/usr/local/bin/sync -> /opt/.../bash/sync.sh`
# install still finds `.env` next to the real script.
SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
ENV_FILE="${SCRIPT_DIR}/.env"

if [ ! -f "${ENV_FILE}" ]; then
    echo "Missing config file: ${ENV_FILE}" >&2
    exit 1
fi

# `sync-kill.sh` does not read .env, so a LOCK_FILE there would desync the
# two scripts. Snapshot the process-env value before sourcing and restore it
# after, so only the invocation environment can override LOCK_FILE.
__user_lock_file="${LOCK_FILE-}"
set -a
# shellcheck source=/dev/null
. "${ENV_FILE}"
set +a
LOCK_FILE="$__user_lock_file"
unset __user_lock_file

HI_SPEED_LIMIT="${HI_SPEED_LIMIT:-50M}"
LOW_SPEED_LIMIT="${LOW_SPEED_LIMIT:-1M}"
HI_SPEED_START_HOUR="${HI_SPEED_START_HOUR:-23}"
HI_SPEED_END_HOUR="${HI_SPEED_END_HOUR:-6}"
LOG_FILE="${LOG_FILE:-${SCRIPT_DIR}/sync_log.out}"
MAX_AGE="${MAX_AGE:-2d}"
EXCLUDE="${EXCLUDE:-*.part}"

# Parse args before required-var checks so --source can substitute a missing
# SOURCE in .env (and likewise for any future overrides).
SOURCE="${SOURCE-}"
while [ "$#" -gt 0 ]; do
    case "$1" in
        --max-age)
            [ "$#" -ge 2 ] || { echo "--max-age requires a value" >&2; exit 1; }
            MAX_AGE="$2"
            shift 2
            ;;
        --source)
            [ "$#" -ge 2 ] || { echo "--source requires a value" >&2; exit 1; }
            SOURCE="$2"
            shift 2
            ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

: "${SOURCE:?SOURCE must be set in ${ENV_FILE} or via --source}"
: "${DESTINATION:?DESTINATION must be set in ${ENV_FILE}}"

# Reject unfilled placeholders from .env.example
for var in SOURCE DESTINATION; do
    if [[ "${!var}" == "<"*">" ]]; then
        echo "$var still holds placeholder ${!var} — edit ${ENV_FILE}" >&2
        exit 1
    fi
done

############################################################

# Check if already running. `LOCK_FILE` default must match `sync-kill.sh`.
LOCK_FILE="${LOCK_FILE:-/tmp/sync_script.lock}"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "Sync script is already running. Skipping."
    exit 1
fi

# Pick speed limit by current hour. Range is [start, end) and may wrap past
# midnight (e.g. 23..6 = nightly window). When start < end the window is a
# normal daytime span (e.g. 8..18) and the test must be AND, not OR — using
# OR there would match every hour of the day.
TIME_HOURS=$(date +"%-H")
if [ "${HI_SPEED_START_HOUR}" -gt "${HI_SPEED_END_HOUR}" ]; then
    # wraparound window
    if [ "${TIME_HOURS}" -ge "${HI_SPEED_START_HOUR}" ] || [ "${TIME_HOURS}" -lt "${HI_SPEED_END_HOUR}" ]; then
        SPEED_LIMIT=${HI_SPEED_LIMIT}
    else
        SPEED_LIMIT=${LOW_SPEED_LIMIT}
    fi
else
    # same-day window
    if [ "${TIME_HOURS}" -ge "${HI_SPEED_START_HOUR}" ] && [ "${TIME_HOURS}" -lt "${HI_SPEED_END_HOUR}" ]; then
        SPEED_LIMIT=${HI_SPEED_LIMIT}
    else
        SPEED_LIMIT=${LOW_SPEED_LIMIT}
    fi
fi

mkdir -p "$(dirname "$LOG_FILE")"

# `-P` (rclone progress) only on a tty. Cron logs would otherwise fill with
# carriage-return refresh frames.
PROGRESS=()
if [ -t 1 ]; then
    PROGRESS=(-P)
fi

# Run the command. `tee` (not `tee -a`) is intentional — only the most recent
# run is interesting for post-mortem; older logs would just bloat the file.
#
# Note: rclone reads its config from the invoking user's
# `~/.config/rclone/rclone.conf`. When run from root cron, this is root's
# config — make sure the remote is configured there, or pass `--config`.
rclone copy "$SOURCE" "$DESTINATION" \
  "${PROGRESS[@]}" --transfers=1 --checkers=1 --multi-thread-streams=0 \
  --bwlimit="$SPEED_LIMIT" \
  --max-age "$MAX_AGE" \
  --exclude "$EXCLUDE" \
  2>&1 | tee "$LOG_FILE"

exit 0
