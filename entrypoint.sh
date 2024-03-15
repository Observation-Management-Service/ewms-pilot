#!/bin/bash
echo "entrypoint: activating venv"
source /app/entrypoint_venv/bin/activate
echo "entrypoint: executing command: $@"
exec "$@"