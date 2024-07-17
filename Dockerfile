ARG PYTHON=3.12

FROM python:${PYTHON}

# installs
RUN apt-get update && \
    apt-get -qy full-upgrade && \
    apt-get install -qy curl && \
    curl -sSL https://get.docker.com/ | sh

# user
RUN useradd -m -U app

# dirs
RUN mkdir /app
RUN chown -R app /app
WORKDIR /app
#
RUN mkdir -p /ewms-pilot
RUN chown -R app /ewms-pilot

# entrypoint magic
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# user
USER app
COPY --chown=app:app . .

# python: venv and install
RUN pip install virtualenv
RUN python -m virtualenv /app/entrypoint_venv
ARG FLAVOR="rabbitmq"
RUN . /app/entrypoint_venv/bin/activate && \
    pip install --upgrade pip && \
    pip install --no-cache-dir .[${FLAVOR}]

# go
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "ewms_pilot"]
