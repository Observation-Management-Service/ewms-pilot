#!/bin/bash
set -ex

########################################################################
#
# Wait on this list of pids given
#
########################################################################

if [ -z "$1" ]; then
    echo "Usage: wait-on-pids.sh PIDS_LIST"
    exit 1
else
    PIDS_LIST="$1"
fi


echo "--------------------------------------------------------------"
echo "will wait on pids: $PIDS_LIST..."


# wait for tests to finish
# https://stackoverflow.com/a/32604828/13156561
sleep 3  # short sleep to help logs
for pid in PIDS_LIST; do
    date --rfc-3339=seconds
    echo "waiting for $pid..."
    if ! wait -n $pid; then
        echo "ERROR: test(s) failed"
        sleep 5  # may need to wait for output files to be written
        kill $PIDS_LIST 2>/dev/null
        exit 1
    fi
    echo "-> PASSED"
done
