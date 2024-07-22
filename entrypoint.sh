#!/bin/bash
echo "entrypoint: activating docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 &
sleep 1
# TODO: remove this and put in ci cmd
docker pull python:alpine
echo "entrypoint: activating venv"
source /app/entrypoint_venv/bin/activate
echo "entrypoint: executing command: $@"
exec "$@"
