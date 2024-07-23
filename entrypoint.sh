#!/bin/bash

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                      ║"
echo "║                    Entering the Task Pilot Container Environment                     ║"
echo "║                                                                                      ║"
echo "║                      for the Event Workflow Management System                        ║"
echo "║                                                                                      ║"
echo "╠══════════════════════════════════════════════════════════════════════════════════════╣"
echo "║  Source: https://github.com/Observation-Management-Service/ewms-pilot                ║"
echo "║  Today:  $(date --rfc-3339=seconds)                                                   ║"  # spacing for command
echo "╠══════════════════════════════════════════════════════════════════════════════════════╣"
while read -r i; do printf "║  %-83s ║\n" "$i"; done <<< "$(pip freeze)"  # pip-supplied info
echo "╚══════════════════════════════════════════════════════════════════════════════════════╝"

echo "entrypoint: activating docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 || echo "WARNING: docker-in-docker setup failed (error suppressed)" &
sleep 1

echo "----"
echo "entrypoint: activating venv"
source /app/entrypoint_venv/bin/activate

echo "----"
echo "entrypoint: executing command: $@"

echo "----"
exec "$@"
