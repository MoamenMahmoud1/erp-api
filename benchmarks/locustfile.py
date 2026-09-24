import os

from locust import HttpUser, between, task
from locust.exception import StopUser


DASHBOARD_PATH = os.getenv(
    "BENCHMARK_PATH",
    "/api/v1/accounting/analytics/overview/",
)

JWT_TOKEN = os.getenv("JWT_TOKEN", "").strip()
JWT_TOKENS = tuple(
    token.strip()
    for token in os.getenv("JWT_TOKENS", "").split(",")
    if token.strip()
)

COMMON_HEADERS = {
    "Accept": "application/json",
    "X-Forwarded-Proto": "https",
}


class DashboardUser(HttpUser):
    """One virtual user sends exactly one dashboard request."""

    wait_time = between(0, 0)

    @task
    def dashboard(self):
        if JWT_TOKENS:
            token = JWT_TOKENS[hash(self) % len(JWT_TOKENS)]
        else:
            token = JWT_TOKEN

        if not token:
            raise RuntimeError(
                "Dashboard benchmark requires JWT_TOKEN or JWT_TOKENS."
            )

        with self.client.get(
            DASHBOARD_PATH,
            headers={
                **COMMON_HEADERS,
                "Authorization": f"Bearer {token}",
            },
            name="dashboard_overview",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )

        raise StopUser


class AuthUser(HttpUser):
    """One virtual user performs CSRF + login exactly once."""

    wait_time = between(0, 0)

    def on_start(self):
        identifier = os.getenv("ERP_USERNAME", "").strip()
        password = os.getenv("ERP_PASSWORD", "")

        if not identifier or not password:
            raise RuntimeError(
                "Auth benchmark requires ERP_USERNAME and ERP_PASSWORD."
            )

        csrf = self.client.get(
            "/api/v1/auth/csrf/",
            headers=COMMON_HEADERS,
            name="auth_csrf",
        )

        if csrf.status_code != 200:
            raise RuntimeError(f"CSRF failed: HTTP {csrf.status_code}")

        try:
            csrf_token = csrf.json()["csrf_token"]
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("CSRF response did not contain csrf_token.") from exc

        response = self.client.post(
            "/api/v1/auth/login/",
            json={
                "identifier": identifier,
                "password": password,
            },
            headers={
                **COMMON_HEADERS,
                "Content-Type": "application/json",
                "X-CSRFToken": csrf_token,
            },
            name="auth_login",
        )

        if response.status_code != 200:
            raise RuntimeError(f"Login failed: HTTP {response.status_code}")

    @task
    def stop(self):
        raise StopUser
