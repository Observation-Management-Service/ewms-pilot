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

# apptainer-in-apptainer via Debian backports when needed
RUN if [ "$CONTAINER_PLATFORM" = "apptainer" ]; then \
      set -eux; \
      . /etc/os-release; \
      echo "deb http://deb.debian.org/debian ${VERSION_CODENAME}-backports main" \
        > /etc/apt/sources.list.d/backports.list; \
      apt-get update; \
      # Prefer backports if available; otherwise try normal repo
      if apt-cache policy apptainer | grep -q "${VERSION_CODENAME}-backports"; then \
        apt-get install -y -t ${VERSION_CODENAME}-backports apptainer; \
      else \
        apt-get install -y apptainer || true; \
      fi; \
      apt-get install -y --no-install-recommends fuse3 squashfs-tools uidmap; \
      rm -rf /var/lib/apt/lists/*; \
    else \
      echo "not installing apptainer"; \
    fi


# dirs
#
# the WORKDIR
RUN mkdir /app
WORKDIR /app

# entrypoint magic
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


# Mount the entire build context (including '.git/') just for this step
# NOTE:
#  - mounting '.git/' allows the Python project to build with 'setuptools-scm'
#  - no 'COPY .' because we don't want to copy extra files (especially '.git/')
#  - using '/tmp/pip-cache' allows pip to cache
RUN --mount=type=cache,target=/tmp/pip-cache \
    pip install --upgrade "pip>=25" "setuptools>=80" "wheel>=0.45"
RUN pip install virtualenv
RUN python -m virtualenv /app/entrypoint_venv
ARG FLAVOR="rabbitmq"
RUN --mount=type=bind,source=.,target=/src,rw \
    --mount=type=cache,target=/tmp/pip-cache \
    bash -euxo pipefail -c '\
      . /app/entrypoint_venv/bin/activate && \
      pip install --upgrade pip && \
      pip install --no-cache-dir /src[${FLAVOR}] \
    '


# go
# use shell form to pass in var -- https://stackoverflow.com/a/37904830/13156561
ENTRYPOINT ["/entrypoint.sh"]
# note: ^^^ entrypoint activates the python virtual env
CMD ["python", "-m", "ewms_pilot"]
