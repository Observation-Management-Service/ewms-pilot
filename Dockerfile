ARG PYTHON=3.12

FROM python:${PYTHON}

# NOTE: On Docker-in-Docker...
#       After much tinkering to get docker-in-docker working, it was decided to run as root user.
#       The predominant issue was launching the docker daemon on run, which normally needs root access.
#       - This was considerend: https://github.com/nestybox/sysbox/issues/784#issuecomment-1981733086
#           but ultimately this either neeeded
#               A. a username/password on run (interactive) which uses systemd, or
#               B. alpine linux (supervisord), which seems to incompatible with the 'htcondor' pythoon package
#       - An alternative would be rootless docker: https://docs.docker.com/engine/security/rootless/--
#           this was not explored as it seemed like "too much extra runtime config", and I'm not sure
#           how this would translate to apptainer.


ARG CONTAINER_PLATFORM='docker'
ENV _EWMS_PILOT_CONTAINER_PLATFORM="$CONTAINER_PLATFORM"

# docker-in-docker -- see NOTE above
RUN if [ "$CONTAINER_PLATFORM" = "docker" ]; then \
        apt-get update && \
        apt-get -qy full-upgrade && \
        apt-get install -qy curl && \
        curl -sSL https://get.docker.com/ | sh && \
        touch /var/log/dockerd.log ; \
    else \
        echo "not installing docker" ; \
    fi
# ^^^ 'touch' is for starting up docker daemon

# apptainer-in-apptainer
RUN if [ "$CONTAINER_PLATFORM" = "apptainer" ]; then \
        apt update && \
        apt install -y wget && \
        cd /tmp && \
        wget https://github.com/apptainer/apptainer/releases/download/v1.3.3/apptainer_1.3.3_amd64.deb && \
        apt install -y ./apptainer_1.3.3_amd64.deb ; \
    else \
        echo "not installing apptainer" ; \
    fi


# dirs
#
# the WORKDIR
RUN mkdir /app
WORKDIR /app

# entrypoint magic
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# user
COPY . .

# python: venv and install
RUN pip install virtualenv
RUN python -m virtualenv /app/entrypoint_venv
ARG FLAVOR="rabbitmq"
RUN . /app/entrypoint_venv/bin/activate && \
    pip install --upgrade pip && \
    pip install --no-cache-dir .[${FLAVOR}]

# go
# use shell form to pass in var -- https://stackoverflow.com/a/37904830/13156561
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "ewms_pilot"]
