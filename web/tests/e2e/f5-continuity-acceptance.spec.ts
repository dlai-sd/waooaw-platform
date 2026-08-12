// Implements: WC-034 F5/WC-060 Omnichannel Continuity browser acceptance
// Constitutional basis: C-001, C-023, C-042, C-059, C-063

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type APIRequestContext, type BrowserContext } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';
const bpUrl = 'http://127.0.0.1:5001';

async function addSession(context: BrowserContext, projectName: string) {
  const accessToken = `fixture-access-token-${projectName}`;
  const value = await encode({ secret, maxAge: 3600, token: { accessToken, founder: false, sub: `fixture-user-${projectName}` } });
  await context.addCookies([{ name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' }]);
  return accessToken;
}

function headers(accessToken: string, idempotencyKey?: string) {
  return { Authorization: `Bearer ${accessToken}`, ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}) };
}

async function prepare(request: APIRequestContext, accessToken: string, relationshipId: string, idempotencyKey: string, targetChannel = 'WEB') {
  return request.post(`${bpUrl}/api/v1/employment/relationships/${relationshipId}/handoffs`, {
    headers: headers(accessToken, idempotencyKey), data: { targetChannel },
  });
}

async function activate(request: APIRequestContext, accessToken: string, relationshipId: string, handoff: any, targetConversationId = 'web-conversation', extraHeaders = {}) {
  return request.post(`${bpUrl}/api/v1/employment/relationships/${relationshipId}/handoffs/${handoff.handoffId}/activate`, {
    headers: { ...headers(accessToken, handoff.continuityEnvelope.idempotencyKey), ...extraHeaders },
    data: { targetConversationId, continuityEnvelope: handoff.continuityEnvelope },
  });
}

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('UX-CONT-01 UX-CONT-02: prepared source remains active and evidenced activation renders target content', async ({ context, page, request }, testInfo) => {
  test.skip(!['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name), 'Required F5 viewports only.');
  const accessToken = await addSession(context, testInfo.project.name);
  const relationshipId = `relationship-handoff-${testInfo.project.name}`;
  const preparedResponse = await prepare(request, accessToken, relationshipId, 'prepare-and-activate');
  expect(preparedResponse.status()).toBe(201);
  const prepared = await preparedResponse.json();
  expect(prepared.status).toBe('PREPARED');
  expect(prepared.sourceBinding.status).toBe('ACTIVE');

  const activatedResponse = await activate(request, accessToken, relationshipId, prepared);
  expect(activatedResponse.ok()).toBe(true);
  expect((await activatedResponse.json()).resolutionEvidenceId).toBe('evidence-handoff-committed');
  await page.goto(`/relationships/${relationshipId}`);
  await expect(page.getByRole('heading', { level: 1, name: 'DIGITAL_MARKETING relationship' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Emergency Stop' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const contained = await page.locator('.workspace-nav, .workspace-family, .evidence-window').evaluateAll((elements) => elements.every((element) => {
    const bounds = element.getBoundingClientRect();
    return bounds.left >= 0 && bounds.right <= innerWidth;
  }));
  expect(contained).toBe(true);
  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
  await expect(page).toHaveScreenshot('f5-activated-relationship.png', { fullPage: true, animations: 'disabled' });
});

test('UX-CONT-03 UX-CONT-04: timeout preserves source and replay is exact or conflicts without mutation', async ({ request }, testInfo) => {
  const accessToken = `fixture-access-token-${testInfo.project.name}`;
  const relationshipId = `relationship-replay-${testInfo.project.name}`;
  const firstResponse = await prepare(request, accessToken, relationshipId, 'stable-replay');
  const prepared = await firstResponse.json();
  const timedOut = await activate(request, accessToken, relationshipId, prepared, 'timeout');
  expect(timedOut.status()).toBe(503);
  expect((await timedOut.json()).title).toContain('source remains authoritative');

  const replay = await prepare(request, accessToken, relationshipId, 'stable-replay');
  expect((await replay.json()).replayed).toBe(true);
  const divergent = await prepare(request, accessToken, relationshipId, 'stable-replay', 'WHATSAPP');
  expect(divergent.status()).toBe(409);
  expect((await divergent.json()).code).toBe('IDEMPOTENCY_CONFLICT');
});

test('UX-CONT-05: downgrade and cross-tenant attempts disclose no relationship content', async ({ request }, testInfo) => {
  const accessToken = `fixture-access-token-${testInfo.project.name}`;
  const relationshipId = `relationship-denial-${testInfo.project.name}`;
  const prepared = await (await prepare(request, accessToken, relationshipId, 'denial')).json();
  for (const response of [
    await activate(request, accessToken, relationshipId, prepared, 'downgrade'),
    await activate(request, accessToken, relationshipId, prepared, 'web-conversation', { 'X-Fixture-Tenant': 'foreign' }),
  ]) {
    expect(response.status()).toBe(404);
    const body = await response.text();
    expect(body).not.toContain(relationshipId);
    expect(body).not.toContain('fixture-participant');
  }
});

test('UX-CONT-06 UX-RES-02: Stop preempts handoff and reconnect cannot claim or release continuity', async ({ page, request }, testInfo) => {
  const accessToken = `fixture-access-token-${testInfo.project.name}`;
  const relationshipId = `relationship-stopped-${testInfo.project.name}`;
  const prepared = await (await prepare(request, accessToken, relationshipId, 'stop-preempts')).json();
  const stopped = await request.post(`${bpUrl}/api/v1/employment/relationships/${relationshipId}/emergency-stop`, {
    headers: headers(accessToken), data: { correlationId: 'c0000000-0000-4000-8000-000000000001' },
  });
  expect(stopped.ok()).toBe(true);
  expect((await activate(request, accessToken, relationshipId, prepared)).status()).toBe(409);

  await page.goto(`/relationships/${relationshipId}`);
  await expect(page.getByText('Evaluation · STOPPED_EMERGENCY')).toBeVisible();
  await expect(page.getByText('stopped', { exact: true })).toBeVisible();
  await expect(page.getByText('live', { exact: true })).toHaveCount(0);
  await expect(page.getByLabel('Message your professional')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Send' })).toBeDisabled();
  await expect(page.getByText(/committed handoff|continuity complete|synchronized/i)).toHaveCount(0);
  if (['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name)) {
    await expect(page).toHaveScreenshot('f5-stopped-relationship.png', { fullPage: true, animations: 'disabled' });
  }
});