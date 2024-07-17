ARG PYTHON=3.12
ARG FLAVOR="rabbitmq"

FROM python:${PYTHON}

RUN useradd -m -U app

RUN mkdir /app
WORKDIR /app
RUN chown -R app /app

# entrypoint magic
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# user
USER app
COPY --chown=app:app . .

# venv and install
RUN pip install virtualenv
RUN python -m virtualenv /app/entrypoint_venv
RUN . /app/entrypoint_venv/bin/activate && \
    pip install --upgrade pip && \
    pip install --no-cache-dir .[${FLAVOR}]

# go
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "ewms_pilot"]
