#!/usr/bin/env bash
set -euo pipefail

############################################################
# Readme
############################################################
# Stops a running sync.sh process by killing the process group
# that holds the lock file used by sync.sh.

# Default must match `sync.sh`.
LOCK_FILE="${LOCK_FILE:-/tmp/sync_script.lock}"

if [ ! -e "$LOCK_FILE" ]; then
    echo "Sync is not running (no lock file at $LOCK_FILE)."
    exit 0
fi

# Without fuser, an empty PID below would be misread as "stale lock" and the
# active sync's lock file would be deleted. Bail loudly instead.
if ! command -v fuser >/dev/null 2>&1; then
    echo "fuser not found — install psmisc (apt install psmisc)." >&2
    exit 1
fi

# fuser separates multiple PIDs with whitespace (tabs on some distros);
# awk grabs the first field and tolerates either.
SYNC_PID=$(fuser "$LOCK_FILE" 2>/dev/null | awk '{print $1}' || true)

if [ -z "$SYNC_PID" ]; then
    echo "Lock file exists but no process holds it; removing stale lock."
    rm -f "$LOCK_FILE"
    exit 0
fi

PGID=$(ps -o pgid= -p "$SYNC_PID" | tr -d ' ')
echo "Stopping sync (PID $SYNC_PID, PGID $PGID)..."
kill -TERM -"$PGID"

for _ in 1 2 3 4 5; do
    if ! kill -0 "$SYNC_PID" 2>/dev/null; then
        echo "Stopped."
        exit 0
    fi
    sleep 1
done

echo "Process did not exit after SIGTERM; sending SIGKILL."
kill -KILL -"$PGID" 2>/dev/null || true
echo "Stopped."
