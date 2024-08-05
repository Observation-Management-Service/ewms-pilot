#!/bin/bash
set -ex

########################################################################
#
# Wait on this list of pids given
#
########################################################################

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: wait-on-pids.sh PIDS_LIST DONE_PHRASE"
    exit 1
else
    PIDS_LIST="$1"
    DONE_PHRASE="$2"
fi


echo "--------------------------------------------------------------"
echo "will wait on pids: $PIDS_LIST..."


# https://stackoverflow.com/a/32604828/13156561
for pid in $PIDS_LIST; do
    date --rfc-3339=seconds
    echo "waiting for $pid..."
    if ! wait -n $pid; then
        echo "ERROR: pid $pid exited with non-zero code"
        sleep 5  # may need to wait for output files to be written
        kill $PIDS_LIST 2>/dev/null
        exit 1
    fi
    echo "-> $DONE_PHRASE"
done
