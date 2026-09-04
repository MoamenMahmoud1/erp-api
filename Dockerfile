# Production WSGI deployment image.
#
# Build:  docker build -t erp-api:latest .
# Run:    docker run -p 8000:8000 \
#           -e DJANGO_SETTINGS_MODULE=core.settings.settings_prod \
#           -e DB_HOST=postgres ... erp-api:latest
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim AS base

# System dependencies (psycopg + Pillow).
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

RUN DJANGO_SETTINGS_MODULE=core.settings.settings_prod python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["sh", "-c", "exec gunicorn -c gunicorn.conf.py core.wsgi:application"]
