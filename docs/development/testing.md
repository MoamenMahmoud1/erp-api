# Test Architecture

The test suite is organized around business domains and responsibilities rather than one large application-wide test run.

## Repository layout

```text
accounts/tests/
  test_login_serializer.py
  test_login_view.py
  test_signup_verification.py
  test_email_change.py
  test_password_reset.py
  test_password_change.py
  test_logout_view.py
  test_refresh_view.py
  test_role_hierarchy.py
  test_employee_visibility.py
  test_employee_organization.py
  test_employee_organization_api.py

authsession/tests/
  test_http.py
  test_session_api.py
  ...

products/tests/
  test_models.py
  test_product_api.py
  test_carton_pricing_api.py
  test_intelligence.py
  test_intelligence_api.py

organization/tests/
  test_company.py
  test_metrics.py
  test_site.py
  test_department.py
```

The same rule applies to the remaining apps: model/constraint tests stay separate from query tests, domain services, and HTTP/API contracts.

## Shared test infrastructure

`core.testing.auth` owns the stateful login setup used by API tests. It performs the real login endpoint and carries the `refresh_token` and signed `device_id` cookies into the API client. This keeps stateful authentication tests faithful to production without duplicating cookie plumbing in every suite.

Stateless JWT tests remain separate and use direct token authentication because they intentionally verify zero-database authentication behavior.

## Test layers

### Model and database constraints

Use these tests for normalization, validation, uniqueness, check constraints, and database-level invariants.

### Query and visibility

Use these tests for reusable queryset behavior, scoping, visibility, and query-count expectations.

### Domain services

Use these tests for business rules and transactional workflows such as invoice lifecycle, collection/refunds, inventory movements, purchase returns, and sales returns.

### API contracts

Use these tests for serializer/view behavior, HTTP status codes, permissions, pagination, and response payloads. API tests should exercise the real authentication path when the endpoint depends on an auth session.

### Operational counters

`organization.tests.test_metrics` verifies that master-data counters update on normal creates/deletes and that the daily reconciliation service repairs deliberate counter drift. `core.tests.test_celery` verifies that Celery is wired correctly and that only the daily counter reconciliation is scheduled currently.

Product intelligence has both service-level and API contract coverage. Dashboard analytics tests remain live; they do not depend on report-cache warming.

## Local commands

Run everything:

```bash
python manage.py test
```

Run one app:

```bash
python manage.py test invoices
```

Run one responsibility:

```bash
python manage.py test invoices.tests.test_lifecycle
python manage.py test payments.tests.test_collection
python manage.py test organization.tests.test_metrics
python manage.py test core.tests.test_celery
python manage.py test products.tests.test_intelligence products.tests.test_intelligence_api
```

Run one test class or method:

```bash
python manage.py test invoices.tests.test_lifecycle.InvoiceLifecycleTests
python manage.py test invoices.tests.test_lifecycle.InvoiceLifecycleTests.test_confirm_consumes_stock
```

## CI suites

GitHub Actions runs the suite in parallel by domain:

| Suite | Django apps |
| --- | --- |
| authentication | `accounts authsession authentication` |
| organization | `organization customers suppliers` |
| catalog | `products coupons` |
| sales | `invoices payments inventory` |
| purchasing | `purchases` |

A failure therefore points to the business area that needs attention while other suites continue running.
