#!/bin/bash

########################################################################
#
# Docker container entrypoint
#
########################################################################

echo "ENTRYPOINT: $@"
if [ -z "$1" ]; then
    echo "Usage: entrypoint.sh CONTAINER_PLATFORM"
    exit 1
fi
export _EWMS_PILOT_CONTAINER_PLATFORM="$1"  # used in pilot


echo ""
echo "Setting up the EWMS Task Pilot Container Environment..."

echo "----"
printenv
echo "----"

# setup the directory exposed to all tasks -- this is done here instead of in Dockerfile so to work with singularity
export EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST="${EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST:-$PWD}"
mkdir -p "$EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST/ewms-pilot-data/"
mkdir -p "$EWMS_PILOT_DATA_DIR_PARENT_PATH_ON_HOST/ewms-pilot-data/data-hub"

# inspect the file system
echo "----"
echo "PWD: $PWD"
ls -l $PWD


if [[ "$_EWMS_PILOT_CONTAINER_PLATFORM" == "docker" ]]; then
# check docker -- https://stackoverflow.com/a/48843074/13156561
    echo "----"
    if (! docker stats --no-stream ); then
        echo "Activating docker daemon..."
        dockerd > ./dockerd.log 2>&1 & dockerd_pid="$!"
        # dockerd > /var/log/dockerd.log 2>&1 || echo "WARNING: docker-in-docker setup failed (error suppressed)" &
        i=0
        while (! docker stats --no-stream ); do
            # Docker takes a few seconds to initialize
            echo "Waiting for docker daemon to initialize..."
            # start up failed? -> break
            #    wait for 2s then, if dockerd_pid didn't exit with a non-0, continue on
            sleep 2 & sleeper_pid="$!"  # this should never fail (always exits 0)
            if ! wait -n $dockerd_pid $sleeper_pid; then
                # ^^^^^^ this returns on FIRST done
                echo "ERROR: docker daemon failed to activate"
                break
            fi
            # taking too long? -> break
            i=$((i+1))
            if [[ "$i" == "60" ]]; then
                break
            fi
        done
        cat ./dockerd.log  # TODO - trim down?
    fi
    docker info
fi

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
