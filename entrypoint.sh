#!/bin/bash

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                      ║"
echo "║                                                                                      ║"
echo "║                       Entering the Pilot Container Environment                       ║" 
echo "║                                                                                      ║"
echo "║                       for the Event Workflow Management System                       ║"
echo "║                                                                                      ║"
echo "║                                                                                      ║"
echo "╠══════════════════════════════════════════════════════════════════════════════════════╣"
echo "║                                                                                      ║"
echo "║  Source: https://github.com/Observation-Management-Service/ewms-pilot                ║"
echo "║  Today:  $(date --rfc-3339=seconds)                                                  ║"
echo "║                                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════╝"
echo ""

echo "----"
echo "entrypoint: activating docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 || echo "WARNING: docker-in-docker setup failed (error suppressed)" &
sleep 1

echo "----"
echo "entrypoint: activating venv"
source /app/entrypoint_venv/bin/activate

echo "----"
echo "entrypoint: executing command: $@"
exec "$@"
