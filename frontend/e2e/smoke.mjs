import { chromium } from '@playwright/test';

const baseUrl = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173';
const username = process.env.E2E_USERNAME;
const password = process.env.E2E_PASSWORD;

if (!username || !password) {
  throw new Error('E2E_USERNAME and E2E_PASSWORD must be provided.');
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

let forcedExpiredAccess = false;
let refreshCalls = 0;

await page.route('**/api/v1/accounting/analytics/overview/**', async (route) => {
  if (!forcedExpiredAccess && route.request().method() === 'GET') {
    forcedExpiredAccess = true;
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Authentication credentials were not provided.' }),
    });
    return;
  }
  await route.continue();
});

page.on('response', async (response) => {
  const url = response.url();
  if (url.includes('/auth/refresh/')) {
    refreshCalls += 1;
  }
  if (url.includes('/api/v1/')) {
    console.log(`API ${response.status()} ${response.request().method()} ${url.replace(baseUrl, '')}`);
  }
});

page.on('response', async (response) => {
  const url = response.url();
  if (url.includes('/api/v1/')) {
    console.log(`API ${response.status()} ${response.request().method()} ${url.replace(baseUrl, '')}`);
  }
});

try {
  const readiness = await page.request.get('http://127.0.0.1:8000/health/ready/');
  if (!readiness.ok()) {
    throw new Error(`Backend readiness failed: ${readiness.status()} ${await readiness.text()}`);
  }

  await page.goto(baseUrl, { waitUntil: 'networkidle' });

  await page.getByRole('textbox', { name: 'Username or email' }).fill(username);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForTimeout(3000);
  console.log(`After login URL: ${page.url()}`);
  console.log(`After login body: ${(await page.locator('body').innerText()).slice(0, 4000)}`);

  await page.getByRole('heading', { name: 'Dashboard', exact: true }).waitFor({
    state: 'visible',
    timeout: 15_000,
  });
  await page.getByText('Net sales', { exact: true }).waitFor({
    state: 'visible',
    timeout: 15_000,
  });

  if (!forcedExpiredAccess || refreshCalls < 1) {
    throw new Error(`Automatic access-token refresh was not exercised. forced401=${forcedExpiredAccess}, refreshCalls=${refreshCalls}`);
  }

  console.log('Web E2E passed: login -> forced expired access token -> automatic refresh -> dashboard.');
} catch (error) {
  await page.screenshot({ path: 'e2e-failure.png', fullPage: true }).catch(() => {});
  throw error;
} finally {
  await browser.close();
}
