import http from 'k6/http';
import { check, fail } from 'k6';

const BASE_URL = (__ENV.BASE_URL || 'http://127.0.0.1:8080').replace(/\/$/, '');
const IDENTIFIER = __ENV.ERP_USERNAME;
const PASSWORD = __ENV.ERP_PASSWORD;

const TOKEN_POOL = (__ENV.JWT_TOKENS || '')
  .split(',')
  .map((token) => token.trim())
  .filter(Boolean);

const VUS = Number(__ENV.VUS || 1000);
const ITERATIONS = Number(__ENV.ITERATIONS || 10000);
const MAX_DURATION = __ENV.MAX_DURATION || '10m';

const COMMON_HEADERS = {
  Accept: 'application/json',
  'X-Forwarded-Proto': 'https',
};

export const options = {
  discardResponseBodies: true,
  maxRedirects: 0,

  scenarios: {
    dashboard_10k: {
      executor: 'shared-iterations',
      vus: VUS,
      iterations: ITERATIONS,
      maxDuration: MAX_DURATION,
    },
  },

  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(50)<1000', 'p(95)<2000', 'p(99)<5000'],
    checks: ['rate>0.99'],
  },
};

function login() {
  const csrfResponse = http.get(
    `${BASE_URL}/api/v1/auth/csrf/`,
    {
      headers: COMMON_HEADERS,
      tags: { endpoint: 'auth_csrf' },
    },
  );

  check(csrfResponse, {
    'csrf bootstrap is 200': (response) => response.status === 200,
    'csrf bootstrap has token': (response) => Boolean(response.json('csrf_token')),
  });

  if (csrfResponse.status !== 200) {
    fail(`CSRF bootstrap failed: HTTP ${csrfResponse.status}`);
  }

  const csrf = csrfResponse.json('csrf_token');
  if (!csrf) {
    fail('CSRF token missing.');
  }

  const csrfCookie = csrfResponse.cookies.csrftoken?.[0]?.value || '';

  const loginResponse = http.post(
    `${BASE_URL}/api/v1/auth/login/`,
    JSON.stringify({
      identifier: IDENTIFIER,
      password: PASSWORD,
    }),
    {
      headers: {
        ...COMMON_HEADERS,
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
      },
      cookies: {
        csrftoken: csrfCookie,
      },
      tags: { endpoint: 'auth_login' },
    },
  );

  check(loginResponse, {
    'login is 200': (response) => response.status === 200,
    'login returned access token': (response) => Boolean(response.json('access')),
  });

  if (loginResponse.status !== 200) {
    fail(`Login failed: HTTP ${loginResponse.status}`);
  }

  const accessToken = loginResponse.json('access');

  if (!accessToken) {
    fail('Login response did not contain an access token.');
  }

  return accessToken;
}

export function setup() {
  if (TOKEN_POOL.length === 0 && (!IDENTIFIER || !PASSWORD)) {
    fail('Set ERP_USERNAME and ERP_PASSWORD, or provide JWT_TOKENS.');
  }

  return {
    accessToken: TOKEN_POOL.length > 0 ? null : login(),
  };
}

export default function (data) {
  const accessToken =
    TOKEN_POOL.length > 0
      ? TOKEN_POOL[(__VU - 1) % TOKEN_POOL.length]
      : data.accessToken;

  if (!accessToken) {
    fail('No JWT access token available for this VU.');
  }

  const response = http.get(
    `${BASE_URL}/api/v1/accounting/analytics/overview/`,
    {
      headers: {
        ...COMMON_HEADERS,
        Authorization: `Bearer ${accessToken}`,
      },
      tags: { endpoint: 'dashboard_overview' },
    },
  );

  check(response, {
    'dashboard status is 200': (r) => r.status === 200,
  });
}
