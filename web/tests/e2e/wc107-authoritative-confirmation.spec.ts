// Implements: work-contracts/WC-107-fundamental-customer-journey-integrity.md R015-R016
// Constitutional basis: C-023, C-049, C-059, C-063

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext, actor: string) {
  const value = await encode({
    secret,
    maxAge: 3600,
    token: {
      accessToken: `fixture-access-token-wc107-${actor}`,
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 3600,
      founder: false,
      sub: `fixture-user-wc107-${actor}`,
    },
  });
  await context.addCookies([
    { name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' },
  ]);
}

async function startTrial(page: Page) {
  return page.evaluate(async () => {
    const response = await fetch('/api/acquisition/continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
        professionalVersion: '1.0.0',
        intent: 'trial',
        disclosureRevision: '1.0.0',
        termsVersion: '2026-07-18',
        idempotencyKey: '77777777-7777-4777-8777-777777777777',
      }),
    });
    return { status: response.status, body: await response.json() };
  });
}

async function expectNoOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(
    true
  );
}

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('WC107-R015-R016: Trial confirmation selects and focuses the authoritative card once', async ({ page }, testInfo) => {
  test.skip(
    !['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name),
    'Desktop and compact Chromium prove the spatial contract.'
  );
  const requestUrls: string[] = [];
  const consoleMessages: string[] = [];
  page.on('request', (request) => requestUrls.push(request.url()));
  page.on('console', (message) => consoleMessages.push(message.text()));
  await page.goto('/marketplace');
  const started = await startTrial(page);
  expect(started.status).toBe(200);
  expect(started.body.resumePath).toBe('/professionals/mine');
  await page.goto(started.body.resumePath);

  await expect(page.getByText('Trial started', { exact: true })).toBeVisible();
  const selected = page.locator(
    `.agent-dashboard:visible > li[data-relationship-id="${started.body.relationshipId}"]`
  );
  await expect(selected).toHaveAttribute('data-selected', 'true');
  await expect(selected).toBeFocused();
  expect(await page.locator('.agent-dashboard:visible > li').evaluateAll((cards) => cards.map((card) => card.getAttribute('data-relationship-id'))))
    .toEqual(['relationship-active', 'relationship-second', started.body.relationshipId]);
  expect(new URL(page.url()).pathname).toBe('/professionals/mine');
  expect(new URL(page.url()).search).toBe('');
  expect(await selected.evaluate((card) => getComputedStyle(card).boxShadow)).not.toBe('none');
  await expectNoOverflow(page);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('my-agents-selected.png'), fullPage: true });

  const cdp = await page.context().newCDPSession(page);
  const history = await cdp.send('Page.getNavigationHistory');
  const prohibitedValues = [
    '77777777-7777-4777-8777-777777777777',
    String(started.body.relationshipId),
  ];
  for (const value of prohibitedValues) {
    expect(requestUrls, `request URL leaked ${value}`).not.toEqual(expect.arrayContaining([expect.stringContaining(value)]));
    expect(history.entries.map(({ url }) => url), `browser history leaked ${value}`).not.toEqual(
      expect.arrayContaining([expect.stringContaining(value)])
    );
    expect(consoleMessages.join('\n'), `console log leaked ${value}`).not.toContain(value);
  }

  await page.reload();
  await expect(page.getByText('Trial started', { exact: true })).toHaveCount(0);
  await expect(page.locator('[data-selected="true"]')).toHaveCount(0);
});

test('WC107-R015: paid, zero-price, and pending confirmation text is bounded by server outcome', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'One desktop browser proves the exact outcome copy.');
  const cases = [
    'Payment confirmed. Professional hired.',
    'Professional hired. No payment was due.',
  ];
  for (const confirmation of cases) {
    await page.route('**/professionals/mine/selection', (route) =>
      route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({
          relationshipId: 'relationship-active',
          confirmation,
          nextActionLabel: 'View work',
        }),
      })
    );
    await page.goto('/professionals/mine');
    await expect(page.getByText(confirmation, { exact: true })).toBeVisible();
    await page.unroute('**/professionals/mine/selection');
  }
  await page.route('**/professionals/mine/selection', (route) => route.fulfill({ status: 204 }));
  await page.goto('/professionals/mine');
  await expect(page.getByText(/Trial started|Professional hired|Payment confirmed/)).toHaveCount(0);
});