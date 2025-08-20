ARG PYTHON=3.12

# allow choosing Debian suite; default to bookworm for reliable apptainer
ARG DEBIAN_SUITE=bookworm
FROM python:${PYTHON}-${DEBIAN_SUITE}

ARG CONTAINER_PLATFORM='docker'
ENV _EWMS_PILOT_CONTAINER_PLATFORM="$CONTAINER_PLATFORM"

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

# docker-in-docker (see NOTE above) — fail hard if docker not installed
RUN if [ "$CONTAINER_PLATFORM" = "docker" ]; then \
      set -eux; \
      apt-get update; \
      apt-get -qy full-upgrade; \
      apt-get install -qy curl; \
      curl -sSL https://get.docker.com/ | sh; \
      # verify docker installed; fail build if not
      command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found after install"; exit 1; }; \
      touch /var/log/dockerd.log; \
    else \
      echo "not installing docker"; \
    fi
# ^^^ 'touch' is for starting up docker daemon

# apptainer-in-apptainer — fail hard if not installed; source build uses '--without-suid'
# -- choose apptainer + go versions used when falling back to source
ARG APPTAINER_VERSION=1.3.3
ARG GO_VERSION=1.22.5
RUN \
  # only run this whole block if apptainer mode is requested
  if [ "$CONTAINER_PLATFORM" = "apptainer" ]; then \
    set -eux; \
    export DEBIAN_FRONTEND=noninteractive; \
    . /etc/os-release; \
    apt-get update; \
    \
    # Try native repo first
    if ! apt-get install -y --no-install-recommends apptainer; then \
      echo "WARN: apptainer not in native repo; trying ${VERSION_CODENAME}-backports..."; \
      echo "deb http://deb.debian.org/debian ${VERSION_CODENAME}-backports main contrib non-free non-free-firmware" \
        > /etc/apt/sources.list.d/backports.list; \
      apt-get update; \
      \
      # if also not found in backports...
      if ! apt-get install -y --no-install-recommends -t ${VERSION_CODENAME}-backports apptainer; then \
        echo "WARN: apptainer not found in backports; building from source v${APPTAINER_VERSION}..."; \
        apt-get install -y --no-install-recommends \
          ca-certificates curl git build-essential pkg-config \
          libseccomp-dev libgpgme-dev uidmap squashfs-tools cryptsetup; \
        curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -o /tmp/go.tgz; \
        rm -rf /usr/local/go && tar -C /usr/local -xzf /tmp/go.tgz; \
        export PATH=/usr/local/go/bin:$PATH; \
        go version >/dev/null; \
        git clone --depth 1 --branch "v${APPTAINER_VERSION}" https://github.com/apptainer/apptainer.git /tmp/apptainer; \
        cd /tmp/apptainer; \
        # mconfig needs an explicit choice when user namespaces are disabled; use --without-suid for container builds
        ./mconfig --without-suid; \
        make -C builddir; \
        make -C builddir install; \
        # Verify install
        command -v apptainer >/dev/null || { echo "ERROR: apptainer not found after source build"; exit 1; }; \
        # Trim build deps (optional)
        rm -rf /tmp/apptainer /tmp/go.tgz; \
        apt-get purge -y build-essential git && apt-get autoremove -y && apt-get clean; \
      fi; \
    fi; \
    \
    # always install runtime helpers for apptainer mode
    apt-get install -y --no-install-recommends fuse3 squashfs-tools uidmap; \
    # Final sanity check
    apptainer --version || { echo "ERROR: apptainer not working after install"; exit 1; }; \
    rm -rf /var/lib/apt/lists/*; \
  \
  # if not apptainer mode, just skip installing apptainer
  else \
    echo "not installing apptainer"; \
  fi


# dirs
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
