#!/bin/bash
echo "entrypoint: activating docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 || echo "WARNING: docker-in-docker setup failed (error suppressed)" &
sleep 1
echo "entrypoint: activating venv"
source /app/entrypoint_venv/bin/activate
echo "entrypoint: executing command: $@"
exec "$@"
