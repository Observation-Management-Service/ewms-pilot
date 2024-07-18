#!/bin/bash
echo "entrypoint: activating venv"
source /app/entrypoint_venv/bin/activate
dockerd > /var/log/dockerd.log 2>&1 &
echo "entrypoint: executing command: $@"
exec "$@"
