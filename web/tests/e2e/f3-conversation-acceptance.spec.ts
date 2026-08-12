// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §Conversation and Work, §Constitutional Controls, §Offline, PWA, Privacy, and Resilience
// Constitutional basis: C-001 (Human Override), C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';

function fixtureAccessToken(projectName: string) {
  return `fixture-access-token-${projectName}`;
}

async function addSession(context: BrowserContext, projectName: string) {
  const value = await encode({ secret, maxAge: 60 * 60, token: { accessToken: fixtureAccessToken(projectName), founder: false, sub: `fixture-user-${projectName}` } });
  await context.addCookies([{ name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' }]);
}

async function assertResponsiveAndUnobscured(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const controls = await page.locator('.stop-control button, .conversation-composer').evaluateAll((elements) => elements.map((element) => {
    const bounds = element.getBoundingClientRect();
    const center = document.elementFromPoint(bounds.left + bounds.width / 2, bounds.top + bounds.height / 2);
    return { insideViewport: bounds.left >= 0 && bounds.right <= innerWidth, topmost: center === element || element.contains(center) };
  }));
  expect(controls.every(({ insideViewport, topmost }) => insideViewport && topmost)).toBe(true);
}

function blockingAxeViolations(results: Awaited<ReturnType<AxeBuilder['analyze']>>) {
  return results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious');
}

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('UX-CONV-05 UX-CONV-06 CCT-UX-EF-02 CCT-UX-HO-01: typed status UI is accessible at exact required viewports', async ({ page }, testInfo) => {
  test.skip(!['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name), 'WC034-12 runs only the required Chromium viewports.');
  const bffRequests: string[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/conversations/')) bffRequests.push(request.url());
  });

  await page.goto('/relationships/relationship-active');

  await expect(page.getByText('Here is the current plan.')).toBeVisible();
  await expect(page.getByText('Accepted by WAOOAW')).toBeVisible();
  await expect(page.getByText('Professional processing', { exact: true })).toBeVisible();
  await expect(page.getByText('Evidence pending', { exact: true })).toBeVisible();
  await expect(page.getByText(/Incomplete response/)).toBeVisible();
  await expect(page.getByRole('article', { name: 'plan card' })).toContainText('Increase qualified enquiries');
  await expect(page.getByRole('article', { name: 'action card' })).toContainText('Approve the brief');
  await expect(page.getByRole('article', { name: 'deliverable card' })).toContainText('Campaign brief');
  await expect(page.getByRole('article', { name: 'decision card' })).toContainText('No work starts before selection.');
  await expect(page.getByRole('button', { name: 'View plan' })).toBeDisabled();
  await expect(page.getByText('Evidence recorded')).toHaveCount(0);
  const composer = page.getByLabel('Message your professional');
  await composer.focus();
  await page.keyboard.type('Keyboard draft');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Send' })).toBeFocused();
  const stop = page.getByRole('button', { name: 'Emergency Stop' });
  await expect(stop).toBeVisible();
  await expect(stop).toBeEnabled();
  await assertResponsiveAndUnobscured(page);
  expect(blockingAxeViolations(await new AxeBuilder({ page }).analyze())).toEqual([]);
  expect(bffRequests.some((url) => url.startsWith('http://127.0.0.1:3000/api/conversations/'))).toBe(true);
  expect(bffRequests.every((url) => new URL(url).origin === 'http://127.0.0.1:3000')).toBe(true);
});

test('UX-CONV-01: send remains pending until the same-origin BFF accepts it and announces politely', async ({ page }) => {
  const requests: { method: string; url: string }[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/conversations/')) requests.push({ method: request.method(), url: request.url() });
  });
  await page.goto('/relationships/relationship-send');
  await page.getByLabel('Message your professional').fill('Please summarize today.');
  await page.getByRole('button', { name: 'Send' }).click();

  await expect(page.getByLabel('Conversation timeline').getByText('Please summarize today.')).toBeVisible();
  await expect(page.getByText('Accepted by WAOOAW')).toBeVisible();
  await expect(page.getByText('Professional processing', { exact: true })).toBeVisible();
  await expect(page.getByText('Evidence pending', { exact: true })).toBeVisible();
  await expect(page.locator('[aria-live="polite"]').filter({ hasText: 'Message accepted. Professional processing is pending.' })).toHaveCount(1);
  expect(requests.some(({ method }) => method === 'POST')).toBe(true);
  expect(requests.every(({ url }) => new URL(url).origin === 'http://127.0.0.1:3000')).toBe(true);
});

test('UX-CONV-02 UX-CONV-03: retry reconciles first and preserves one canonical message', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem(
    'waooaw:conversation:relationship-retry:retry:message-relationship-retry',
    'original-idempotency-key',
  ));
  const operations: { method: string; url: string }[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/conversations/relationship-retry')) operations.push({ method: request.method(), url: request.url() });
  });
  await page.goto('/relationships/relationship-retry');
  await page.getByRole('button', { name: 'Retry original message' }).click();

  await expect.poll(() => operations.filter(({ method }) => method === 'POST').length).toBe(1);
  const retryIndex = operations.findIndex(({ method }) => method === 'POST');
  expect(operations.slice(0, retryIndex).some(({ url }) => url.includes('afterCursor='))).toBe(true);
  await expect(page.getByText('Here is the current plan.')).toHaveCount(1);
  await expect(page.locator('[aria-live="polite"]').filter({ hasText: 'Retry accepted for the original message.' })).toHaveCount(1);
});

test('UX-PWA-03 UX-CONV-03 UX-CONV-07: offline outbox reconciles once and remains relationship-local', async ({ context, page }) => {
  const operations: { method: string; url: string; body?: string | null }[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/conversations/relationship-offline')) operations.push({ method: request.method(), url: request.url(), body: request.postData() });
  });
  await page.goto('/relationships/relationship-offline');
  await context.setOffline(true);
  await page.getByLabel('Message your professional').fill('Queue this safely.');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByRole('button', { name: 'Queued' })).toBeDisabled();
  await expect(page.getByText('Unsent on this device')).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('waooaw:conversation:relationship-offline:outbox'))).toContain('Queue this safely.');

  await context.setOffline(false);
  await expect(page.getByText('Accepted by WAOOAW')).toBeVisible();
  await expect.poll(() => operations.filter(({ method }) => method === 'POST').length).toBe(1);
  const postIndex = operations.findIndex(({ method }) => method === 'POST');
  const submitted = JSON.parse(operations[postIndex].body ?? '{}') as { expectedCursor?: string };
  expect(submitted.expectedCursor).toMatch(/^cursor-relationship-offline-/);
  expect(await page.evaluate(() => localStorage.getItem('waooaw:conversation:relationship-offline:outbox'))).toBeNull();

  await page.getByLabel('Message your professional').fill('Private first-professional draft');
  await page.goto('/relationships/relationship-second');
  await expect(page.getByRole('heading', { level: 1, name: /PRIVATE_TUTOR relationship/ })).toBeVisible();
  await expect(page.getByLabel('Message your professional')).toHaveValue('');
  expect(await page.evaluate(() => localStorage.getItem('waooaw:conversation:relationship-offline:draft'))).toBe('Private first-professional draft');
});

test('UX-CONV-04 CCT-UX-HO-02 CCT-UX-HO-03: stream, cancellation, and Stop remain independent', async ({ page }, testInfo) => {
  const ordinaryCommands: string[] = [];
  page.on('request', (request) => {
    if (request.method() !== 'GET') ordinaryCommands.push(new URL(request.url()).pathname);
  });
  await page.goto('/relationships/relationship-stream');
  const composer = page.getByLabel('Message your professional');
  await composer.focus();
  await expect(composer).toBeFocused();
  if (testInfo.project.name === 'webkit-expanded') {
    await page.evaluate(async () => {
      await fetch('/api/conversations/relationship-stream', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'cancel', executionId: '3ead2d21-f908-40b5-9510-b1e77f516d7e', idempotencyKey: 'webkit-cancel' }),
      });
    });
    await page.reload();
  } else {
    await expect(page.locator('[aria-live="polite"]').filter({ hasText: 'Professional response updating: A governed draft update.' })).toHaveCount(1);
    await page.getByRole('button', { name: 'Cancel response' }).click();
  }
  await expect(page.getByText(/Incomplete response · cancelled/i)).toBeVisible();
  expect(ordinaryCommands.some((path) => path === '/api/conversations/relationship-stream')).toBe(true);
  expect(ordinaryCommands.some((path) => path === '/api/emergency-stop')).toBe(false);

  await page.getByRole('button', { name: 'Emergency Stop' }).click();
  await expect(page.getByRole('button', { name: 'Emergency Stop confirmed' })).toBeDisabled();
  await expect(page.getByText('stopped', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Send' })).toBeDisabled();
  expect(ordinaryCommands.some((path) => path === '/api/emergency-stop')).toBe(true);
});

test('CCT-UX-HO-03 UX-RES-01: unknown Stop and send outcomes never become success', async ({ page }) => {
  await page.goto('/relationships/relationship-stop-unknown');
  await page.getByRole('button', { name: 'Emergency Stop' }).click();
  await expect(page.getByRole('button', { name: 'Stop not confirmed. Try again.' })).toBeEnabled();

  await page.goto('/relationships/relationship-unknown');
  await page.getByLabel('Message your professional').fill('Do not assume this arrived.');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.locator('.conversation-error[role="alert"]')).toContainText('The send outcome is unknown.');
  await expect(page.getByText('Send outcome unresolved')).toBeVisible();
  await expect(page.getByText('Evidence recorded')).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem('waooaw:conversation:relationship-unknown:outbox'))).toContain('Do not assume this arrived.');
});

test('CCT-UX-EF-01: evidence turns recorded only after authoritative stream confirmation', async ({ page, request }, testInfo) => {
  await page.goto('/relationships/relationship-evidence');
  await expect(page.getByText('Evidence pending', { exact: true })).toBeVisible();
  const confirmation = await request.post('http://127.0.0.1:5001/__fixtures/conversations/relationship-evidence/record-evidence', {
    headers: { Authorization: `Bearer ${fixtureAccessToken(testInfo.project.name)}` },
  });
  expect(confirmation.ok()).toBe(true);
  if (testInfo.project.name === 'webkit-expanded') await page.reload();
  await expect(page.getByText('Evidence recorded')).toBeVisible();
  await expect(page.getByText('Evidence pending', { exact: true })).toHaveCount(0);
});

test('UX-PWA-03: authenticated conversation payloads remain outside service-worker caches', async ({ page }) => {
  await page.goto('/relationships/relationship-active');
  await expect(page.getByText('Here is the current plan.')).toBeVisible();
  const worker = await page.request.get('/sw.js');
  expect(worker.ok()).toBe(true);
  const workerSource = await worker.text();
  expect(workerSource).toContain('NetworkOnly');
  expect(workerSource).not.toMatch(/relationship payload|accessToken|tenantId|evidence payload/i);
  const cachedUrls = await page.evaluate(async () => {
    const urls: string[] = [];
    for (const cacheName of await caches.keys()) {
      for (const request of await (await caches.open(cacheName)).keys()) urls.push(request.url);
    }
    return urls;
  });
  expect(cachedUrls.filter((url) => /\/api\/conversations\/|\/relationships\/relationship-/.test(url))).toEqual([]);
});