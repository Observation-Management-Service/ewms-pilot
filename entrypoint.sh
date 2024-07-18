#!/bin/bash
echo "entrypoint: activating docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 &
sleep 1
docker ps
echo "entrypoint: activating venv"
source /app/entrypoint_venv/bin/activate
echo "entrypoint: executing command: $@"
exec "$@"
