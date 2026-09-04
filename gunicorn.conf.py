#!/usr/bin/env python3
"""Gunicorn configuration for the ASGI application.

Run with:
    DJANGO_SETTINGS_MODULE=core.settings.settings_prod \
    gunicorn core.asgi:application -c gunicorn.conf.py

Production sizing is intentionally explicit:
    WEB_CONCURRENCY * DB_POOL_MAX_SIZE <= PostgreSQL connection capacity

Set WEB_CONCURRENCY and DB_POOL_MAX_SIZE together in production. The defaults
are conservative starting points, not universal performance-optimal values.
"""
import multiprocessing
import os

cpu_count = max(1, multiprocessing.cpu_count())
default_workers = min(4, cpu_count)
workers = int(os.environ.get("WEB_CONCURRENCY", default_workers))
if workers < 1:
    raise ValueError("WEB_CONCURRENCY must be >= 1")

# Uvicorn ASGI worker from the standalone ``uvicorn-worker`` package.
worker_class = "uvicorn_worker.UvicornWorker"

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

preload_app = True
bind = os.environ.get("BIND", "0.0.0.0:8000")
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info").lower()
capture_output = True

max_requests = int(os.environ.get("MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("MAX_REQUESTS_JITTER", "100"))


def when_ready(server):
    """Called just before the master process is ready to serve requests."""
    server.log.info("Starting ERP API with %d workers", workers)


def on_starting(server):
    """Called just before the master process is about to start."""
    server.log.info("ERP API master process starting")


def on_exit(server):
    """Called when the server is about to exit."""
    server.log.info("ERP API shutting down")
