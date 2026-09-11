# Production WSGI deployment image.
#
# Build the Celery image used by local Compose:
#   docker build --target worker -t erp-api-worker:latest .
#
# Build the Django web image:
#   docker build --target web -t erp-api:latest .
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim AS base

# System dependencies (psycopg + Pillow).
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY docker-entrypoint-web.sh /usr/local/bin/docker-entrypoint-web.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-web.sh && \
    useradd --create-home appuser && \
    chown -R appuser:appuser /app /usr/local/bin/docker-entrypoint-web.sh

# Celery worker/beat image target. It intentionally does not run any
# production-only Django command during the image build.
FROM base AS worker
USER appuser

# The Compose file supplies the concrete Celery worker/beat command.
CMD ["celery", "-A", "core", "worker", "-l", "info"]

# Django WSGI web image target. Production environment is available at
# container runtime, so collectstatic is executed by the entrypoint rather
# than during image build.
FROM base AS web
USER appuser

ENTRYPOINT ["/usr/local/bin/docker-entrypoint-web.sh"]
EXPOSE 8000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "core.wsgi:application"]
