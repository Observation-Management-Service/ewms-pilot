#!/bin/bash

echo "****************************************************************************************"
echo "****************************************************************************************"
echo "**                                                                                    **"
echo "** Entering the Pilot Environment for the Event Workflow Management System (EWMS)     **"
echo "**                                                                                    **"
echo "** -> Source: https://github.com/Observation-Management-Service/ewms-pilot            **"
echo "**                                                                                    **"
echo "****************************************************************************************"
echo "****************************************************************************************"
echo "Today: $(date --rfc-3339=seconds)"

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
