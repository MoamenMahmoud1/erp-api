ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m compileall -q .

COPY docker-entrypoint-web.sh /usr/local/bin/docker-entrypoint-web.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-web.sh && \
    useradd --create-home appuser && \
    chown -R appuser:appuser /app /usr/local/bin/docker-entrypoint-web.sh

FROM base AS worker
USER appuser

# Compose overrides this command for the beat service.
CMD ["celery", "-A", "core", "worker", "-l", "info"]

FROM base AS web
USER appuser

ENTRYPOINT ["/usr/local/bin/docker-entrypoint-web.sh"]
EXPOSE 8000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "core.wsgi:application"]
