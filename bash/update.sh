#!/usr/bin/env bash
set -euo pipefail

############################################################
# Usage
############################################################
# Updates APT packages and (optionally) Docker Compose containers.
#
#   update.sh [--full] [--force-recreate] [--compose-dir=PATH]
#
# Flags:
#   --full              Also run `apt-get dist-upgrade` (may add/remove packages).
#   --force-recreate    Recreate all compose containers even if their image
#                       or config did not change. Default is a graceful
#                       `docker compose up -d` which only recreates containers
#                       with updated images.
#   --compose-dir=PATH  Directory containing docker-compose.yml / compose.yml.
#                       Defaults to the current working directory. If no
#                       compose file is found, the Docker steps are skipped.
#
# Examples:
#   cd /opt/stack && update.sh
#   update.sh --compose-dir=/opt/stack
#   update.sh --full --compose-dir=/opt/stack --force-recreate
############################################################

FULL_UPGRADE=false
FORCE_RECREATE=false
COMPOSE_DIR="$PWD"

for arg in "$@"; do
    case "$arg" in
        --full) FULL_UPGRADE=true ;;
        --force-recreate) FORCE_RECREATE=true ;;
        --compose-dir=*)
            COMPOSE_DIR="${arg#*=}"
            if [ -z "$COMPOSE_DIR" ]; then
                echo "--compose-dir= requires a non-empty path" >&2
                exit 1
            fi
            ;;
        *) echo "Unknown argument: $arg" >&2; exit 1 ;;
    esac
done

echo "Updating packages..."
# Cron-safe APT: never prompt on conffile conflicts, keep installed config.
# Pass DEBIAN_FRONTEND through sudo inline (survives env_reset in sudoers,
# unlike `sudo -E` which needs SETENV).
APT_OPTS=(-y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold)
APT=(sudo DEBIAN_FRONTEND=noninteractive apt-get)

"${APT[@]}" update
"${APT[@]}" "${APT_OPTS[@]}" upgrade
if [ "$FULL_UPGRADE" = true ]; then
    "${APT[@]}" "${APT_OPTS[@]}" dist-upgrade
fi
"${APT[@]}" "${APT_OPTS[@]}" autoremove
"${APT[@]}" clean

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo "docker compose not available — skipping container updates."
    echo "Update complete."
    exit 0
fi

# COMPOSE_DIR defaults to $PWD, so confirm a compose file actually lives there before running
# `docker compose` — otherwise an invocation from an unrelated cwd would silently target nothing.
COMPOSE_FILE=""
for f in compose.yaml compose.yml docker-compose.yaml docker-compose.yml; do
    if [ -f "$COMPOSE_DIR/$f" ]; then
        COMPOSE_FILE="$f"
        break
    fi
done

if [ -z "$COMPOSE_FILE" ]; then
    echo "No compose file in $COMPOSE_DIR — skipping container updates."
    echo "Update complete."
    exit 0
fi

cd "$COMPOSE_DIR"

echo "Pulling latest Docker images..."
docker compose pull

echo "Starting containers..."
if [ "$FORCE_RECREATE" = true ]; then
    docker compose up -d --force-recreate --remove-orphans
else
    docker compose up -d --remove-orphans
fi

echo "Removing dangling Docker images..."
docker image prune -f

echo "Update complete."
