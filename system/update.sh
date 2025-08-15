#!/bin/bash
set -e

FULL_UPGRADE=false
DOCKER_RESTART=false

# Parse command line arguments
for arg in "$@"; do
    if [ "$arg" == "--docker-restart" ]; then
        DOCKER_RESTART=true
    fi
    if [ "$arg" == "--full" ]; then
        FULL_UPGRADE=true
    fi
done

echo "Updating packages..."
sudo apt-get update
sudo apt-get upgrade -y
if [ "$FULL_UPGRADE" = true ]; then
  sudo apt-get dist-upgrade -y
fi
sudo apt-get autoremove -y
sudo apt-get clean

echo "Pulling latest Docker images..."
docker compose pull

if [ "$DOCKER_RESTART" = true ]; then
  echo "Stopping containers..."
  docker compose down
fi

echo "Starting containers..."
docker compose up -d --remove-orphans

echo "Removing unused Docker images..."
docker image prune -a -f

echo "Update complete."
