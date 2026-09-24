import http from 'k6/http';
import { check, fail } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8080';
const IDENTIFIER = __ENV.ERP_USERNAME;
const PASSWORD = __ENV.ERP_PASSWORD;

export const options = {
  discardResponseBodies: true,
  scenarios: {
    burst_10k: {
      executor: 'shared-iterations',
      vus: Number(__ENV.VUS || 1000),
      iterations: 10000,
      maxDuration: __ENV.MAX_DURATION || '10m',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000', 'p(99)<5000'],
    checks: ['rate>0.99'],
  },
};

function login() {
  const csrfResponse = http.get(`${BASE_URL}/api/v1/auth/csrf/`, {
    headers: { Accept: 'application/json' },
  });

  if (csrfResponse.status !== 200) {
    fail(`CSRF bootstrap failed: HTTP ${csrfResponse.status}`);
  }

  let csrf;
  try {
    csrf = csrfResponse.json('csrf_token');
  } catch {
    fail('CSRF bootstrap did not return JSON.');
  }

  if (!csrf) {
    fail('CSRF token missing.');
  }

  const loginResponse = http.post(
    `${BASE_URL}/api/v1/auth/login/`,
    JSON.stringify({ identifier: IDENTIFIER, password: PASSWORD }),
    {
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
      },
      cookies: {
        csrftoken: csrfResponse.cookies.csrftoken?.[0]?.value || '',
      },
    },
  );

  if (loginResponse.status !== 200) {
    fail(`Login failed: HTTP ${loginResponse.status} body=${loginResponse.body}`);
  }

  const access = loginResponse.json('access');
  if (!access) {
    fail('Login response did not contain an access token.');
  }

  return access;
}

export function setup() {
  if (!IDENTIFIER || !PASSWORD) {
    fail('Set ERP_USERNAME and ERP_PASSWORD.');
  }

  return { accessToken: login() };
}

export default function (data) {
  const response = http.get(
    `${BASE_URL}/api/v1/accounting/analytics/overview/`,
    {
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${data.accessToken}`,
      },
      tags: { endpoint: 'dashboard_overview' },
    },
  );

  check(response, {
    'dashboard status is 200': (r) => r.status === 200,
  });
}
