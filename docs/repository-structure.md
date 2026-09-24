# Repository Structure

## Service boundaries

```text
erp-api/
├── backend/       Django project, domain apps, Celery, Gunicorn
├── frontend/      React + TypeScript + Vite + Nginx
├── infra/         Docker Compose and operational/local scripts
├── docs/          Current guidance, history, and design references
└── .github/       CI workflows
```

## Rules

Backend application code belongs under `backend/`. The backend Dockerfile and Gunicorn configuration live with the backend because they build and run that service.

Frontend source and frontend build configuration belong under `frontend/`.

Project-level orchestration belongs under `infra/`. The Compose file builds the backend from `../backend` and the frontend independently.

Current documentation is separated from historical phase notes. Files in `docs/history/` describe previous stages and are not authoritative when they conflict with the current codebase.

The root should contain only repository-wide configuration, documentation entry points, licensing, and shared environment examples.
