#!/bin/bash

echo ""
echo "Setting up the EWMS Task Pilot Container Environment..."

echo "----"
printenv
echo "----"

# setup the directory exposed to all tasks -- this is done here instead of in Dockerfile so to work with singularity
# SINGULARITY_TARGET_DIR is given by condor when run via singularity / apptainer
export EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST="$SINGULARITY_TARGET_DIR"
mkdir -p "$EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST/ewms-pilot-data/"
mkdir -p "$EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST/ewms-pilot-data/data-hub"

# inspect the file system
echo "----"
echo "PWD: $PWD"
ls -l $PWD
echo "----"
echo "EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST: $EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST"
ls -lR $EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST  # recursive
echo "----"
ls -lR /

echo "----"
echo "Activating docker daemon..."
dockerd > /var/log/dockerd.log 2>&1 || echo "WARNING: docker-in-docker setup failed (error suppressed)" &
sleep 1

echo "----"
echo "Activating venv..."
source /app/entrypoint_venv/bin/activate

echo "╔══════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                      ║"
echo "║        - - -       Welcome to the Task Pilot Container Environment       - - -       ║"
echo "║                                                                                      ║"
echo "║        - - -     Part of the Event Workflow Management System (EWMS)     - - -       ║"
echo "║                                                                                      ║"
echo "╠══════════════════════════════════════════════════════════════════════════════════════╣"
echo "║  Source: https://github.com/Observation-Management-Service/ewms-pilot                ║"
echo "║  Today:  $(date --rfc-3339=seconds)                                                   ║"  # spacing for command
echo "╠══════════════════════════════════════════════════════════════════════════════════════╣"
while read -r i; do printf "║  %-83s ║\n" "$i"; done <<< "$(pip show ewms-pilot)"  # pip-supplied info
echo "╚══════════════════════════════════════════════════════════════════════════════════════╝"

echo "Executing command: $@"

echo "----"
exec "$@"
