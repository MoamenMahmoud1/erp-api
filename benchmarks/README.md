# Load benchmark

The benchmark uses Locust (Python) and separates dashboard load from authentication load.

## Dashboard: 10,000 concurrent virtual users

Each virtual user sends exactly one request to the heavy dashboard endpoint:

/api/v1/accounting/analytics/overview/

Use a pre-issued JWT so the benchmark measures the dashboard path instead of password hashing.

```bash
docker run --rm \
  --network host \
  -e JWT_TOKEN="$JWT_TOKEN" \
  -v "$PWD/benchmarks:/benchmarks:ro" \
  locustio/locust \
  -f /benchmarks/locustfile.py \
  --headless \
  --user-classes DashboardUser \
  -u 10000 \
  -r 10000 \
  -t 2m \
  --host http://127.0.0.1:8080
```

You can provide a comma-separated token pool with JWT_TOKENS instead of JWT_TOKEN.

## Authentication: 10,000 concurrent logins

This is a separate stress test for CSRF, login, password hashing, Redis, PostgreSQL, throttling, and AuthSession creation.

```bash
docker run --rm \
  --network host \
  -e ERP_USERNAME="$ERP_USERNAME" \
  -e ERP_PASSWORD="$ERP_PASSWORD" \
  -v "$PWD/benchmarks:/benchmarks:ro" \
  locustio/locust \
  -f /benchmarks/locustfile.py \
  --headless \
  --user-classes AuthUser \
  -u 10000 \
  -r 10000 \
  -t 2m \
  --host http://127.0.0.1:8080
```

## Load-balancer comparison

Run the same dashboard burst with one, two, then four API replicas:

```bash
ENV_FILE=.env.prod.local docker compose --env-file .env.prod.local up -d --build --scale api=1
ENV_FILE=.env.prod.local docker compose --env-file .env.prod.local up -d --scale api=2
ENV_FILE=.env.prod.local docker compose --env-file .env.prod.local up -d --scale api=4
```

The Nginx gateway resolves the api service through Docker DNS. Nginx documents that a hostname resolving to multiple IP addresses defines multiple upstream servers, and the default upstream algorithm is weighted round-robin. Docker Compose exposes scaled services through its internal DNS/service discovery. citeturn158470search0turn158470search4

Monitor during each run:

```bash
watch -n 1 'docker stats --no-stream'
```

PostgreSQL connections:

```bash
docker compose exec db psql -U erp_api -d erp_api -c '
SELECT state, count(*)
FROM pg_stat_activity
GROUP BY state
ORDER BY state;'
```

Compare p50/p95/p99, max latency, failure rate, requests/s, API CPU/RAM, PostgreSQL CPU/connections, Redis CPU/RAM, and gateway CPU/RAM.
