#!/bin/bash
set -euo pipefail
set -ex

########################################################################
#
# Launch a broker specified by $1
#
########################################################################

if [ -z "${1-}" ] || [ -z "${2-}" ]; then
    echo "Usage: run-broker.sh BROKER_TYPE BROKER_CONTAINER_NAME [EXTRA_DOCKER_RUN_OPTIONS]"
    exit 1
else
    BROKER_TYPE="$1"
    BROKER_CONTAINER_NAME="$2"
    EXTRA_DOCKER_RUN_OPTIONS="$3"
fi


echo "--------------------------------------------------------------"
echo "starting broker..."


# Pulsar
if [ "$BROKER_TYPE" = "pulsar" ]; then
    docker run --rm -d --name $BROKER_CONTAINER_NAME $EXTRA_DOCKER_RUN_OPTIONS \
        --shm-size=2g \
        $PULSAR_IMAGE_TAG /bin/bash \
        -c "sed -i s/brokerDeleteInactiveTopicsEnabled=.*/brokerDeleteInactiveTopicsEnabled=false/ /pulsar/conf/standalone.conf && bin/pulsar standalone" \
        >> broker.out 2>&1
# RabbitMQ
elif [ "$BROKER_TYPE" = "rabbitmq" ]; then
    echo -e "log.console.level = debug\n" >> "./rabbitmq-custom.conf"
    echo -e "loopback_users = none\n" >> "./rabbitmq-custom.conf"  # allows guest/guest from non-localhost
    mkdir ./broker_logs
    docker run --rm -d --name $BROKER_CONTAINER_NAME $EXTRA_DOCKER_RUN_OPTIONS \
        --shm-size=2g \
        --env RABBITMQ_USERNAME=guest \
        --env RABBITMQ_PASSWORD=guest \
        --env BITNAMI_DEBUG=true \
        -v $(realpath './rabbitmq-custom.conf'):/bitnami/rabbitmq/conf/custom.conf:ro \
        --mount type=bind,source=$(realpath ./broker_logs),target=/opt/bitnami/rabbitmq/var/log/rabbitmq/ \
        $RABBITMQ_IMAGE_TAG \
        >> broker.out 2>&1
    sleep 10
# NATS
elif [ "$BROKER_TYPE" = "nats" ]; then
    docker run --rm -d --name $BROKER_CONTAINER_NAME $EXTRA_DOCKER_RUN_OPTIONS \
        --shm-size=2g \
        $NATS_IMAGE_TAG -js \
        >> broker.out 2>&1
    sleep 60
else
    echo "ERROR: unknown broker type: $BROKER_TYPE"
    exit 2
fi

sleep 10  # should actually take ~5s
