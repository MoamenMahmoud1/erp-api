import http from 'k6/http';
import { check, fail } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8080';
const TOKEN_POOL = (__ENV.JWT_TOKENS || '')
  .split(',')
  .map((token) => token.trim())
  .filter(Boolean);

export const options = {
  discardResponseBodies: true,
  scenarios: {
    burst_10k: {
      executor: 'per-vu-iterations',
      vus: 100,
      iterations: 100,
      maxDuration: '10m',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000', 'p(99)<5000'],
    checks: ['rate>0.99'],
  },
};

export function setup() {
  if (TOKEN_POOL.length !== 100) {
    fail(`Expected exactly 100 JWT access tokens, got ${TOKEN_POOL.length}.`);
  }

  return { tokens: TOKEN_POOL };
}

export default function (data) {
  const accessToken = data.tokens[__VU - 1];

  const response = http.get(
    `${BASE_URL}/api/v1/accounting/analytics/overview/`,
    {
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      tags: { endpoint: 'dashboard_overview' },
    },
  );

  check(response, {
    'dashboard status is 200': (r) => r.status === 200,
  });
}
