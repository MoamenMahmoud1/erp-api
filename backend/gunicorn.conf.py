#!/usr/bin/env python3
"""Gunicorn configuration for the synchronous WSGI application.

Production sizing is intentionally explicit:
    WEB_CONCURRENCY * DB_POOL_MAX_SIZE <= PostgreSQL connection capacity
"""

import multiprocessing
import os

cpu_count = max(1, multiprocessing.cpu_count())
default_workers = min(4, cpu_count)
workers = int(os.environ.get("WEB_CONCURRENCY", default_workers))
if workers < 1:
    raise ValueError("WEB_CONCURRENCY must be >= 1")

worker_class = "sync"
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
    server.log.info("Starting ERP API with %d workers", workers)


def on_starting(server):
    server.log.info("ERP API master process starting")


def on_exit(server):
    server.log.info("ERP API shutting down")
