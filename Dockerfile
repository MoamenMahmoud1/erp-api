# Production ASGI deployment image.
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

# Install dependencies (layer cached unless requirements change).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source.
COPY . .

# Create a non-root user.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Collect static files (needed for ManifestStaticFilesStorage in prod).
RUN DJANGO_SETTINGS_MODULE=core.settings.settings_prod python manage.py collectstatic --noinput

# Gunicorn starts the ASGI application; the checked-in config owns worker sizing.
# Worker count and DB pool sizing are environment-driven — see gunicorn.conf.py.
EXPOSE 8000
CMD ["sh", "-c", "exec gunicorn -c gunicorn.conf.py core.asgi:application"]
