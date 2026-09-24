# Deployment

Production uses the Django WSGI application, PostgreSQL, Redis, and Celery.

## Required environment

Set these values in the production environment:

- `SECRET_KEY`
- `JWT_SIGNING_KEY`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `REDIS_URL`

Use HTTPS for the web application and API. Keep database and Redis ports private.

## Database deployment

Run migrations as a separate deployment step before starting new web workers:

```bash
cd backend
python manage.py migrate --noinput
```

Do not run migrations from every web container when multiple replicas are deployed.

Create a database backup before schema changes and verify that the backup can be restored.

## Application image

Build the web image from `backend/Dockerfile` with the `web` target:

```bash
docker build --target web -t erp-api-web:release backend
```

The container runs Gunicorn and collects static files during startup.

Build the worker image with the `worker` target and run Celery separately from the web process.

## Health checks

Use:

```text
GET /health/live/
GET /health/ready/
```

`/health/live/` checks process availability. `/health/ready/` checks PostgreSQL and Redis.

## Rollout order

1. Apply database migrations.
2. Deploy the new web image.
3. Deploy the worker image.
4. Check readiness and error logs.
5. Confirm background jobs are running.
6. Keep the previous application image available until the rollout is verified.
