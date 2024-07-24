#!/bin/bash

echo ""
echo "Setting up the EWMS Task Pilot Container Environment..."

echo "----"
echo "TASK-PILOT: activating docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 || echo "WARNING: docker-in-docker setup failed (error suppressed)" &
sleep 1

echo "----"
echo "TASK-PILOT: activating venv..."
source /app/entrypoint_venv/bin/activate

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                      ║"
echo "║         ----       Welcome to the Task Pilot Container Environment       ----        ║"
echo "║                                                                                      ║"
echo "║         ----     Part of the Event Workflow Management System (EWMS)     ----        ║"
echo "║                                                                                      ║"
echo "╠══════════════════════════════════════════════════════════════════════════════════════╣"
echo "║  Source: https://github.com/Observation-Management-Service/ewms-pilot                ║"
echo "║  Today:  $(date --rfc-3339=seconds)                                                   ║"  # spacing for command
echo "╠══════════════════════════════════════════════════════════════════════════════════════╣"
while read -r i; do printf "║  %-83s ║\n" "$i"; done <<< "$(pip show ewms-pilot)"  # pip-supplied info
echo "╚══════════════════════════════════════════════════════════════════════════════════════╝"

echo "TASK-PILOT: executing command: $@"

echo "----"
exec "$@"
