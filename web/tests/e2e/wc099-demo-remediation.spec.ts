// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md R-001–R-018, R-020, R-023
// Constitutional basis: C-001, C-023, C-049, C-059, C-063

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Page, type TestInfo } from '@playwright/test';
import { encode } from 'next-auth/jwt';
import { supportedLocales } from '../../lib/preferences';

const secret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext, projectName: string) {
  const value = await encode({ secret, maxAge: 3600, token: {
    accessToken: `fixture-access-token-wc099-${projectName}`,
    accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 3600,
    founder: false,
    sub: `fixture-user-wc099-${projectName}`,
  } });
  await context.addCookies([{ name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' }]);
}

async function expectNoOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
}

async function attachScreenshot(page: Page, testInfo: TestInfo, name: string) {
  await testInfo.attach(name, { body: await page.screenshot({ animations: 'disabled', fullPage: true }), contentType: 'image/png' });
}

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
  await context.addCookies([
    { name: 'waooaw-locale', value: 'en', domain: '127.0.0.1', path: '/' },
    { name: 'waooaw-theme', value: 'light', domain: '127.0.0.1', path: '/' },
  ]);
});

test('R-001 R-002 R-003: disclosure precedes provider handoff and cancel is inert', async ({ page }, testInfo) => {
  const providerRequests: string[] = [];
  page.on('request', (request) => {
    if (/\/api\/auth\/(signin|callback)|accounts\.google/i.test(request.url())) providerRequests.push(request.url());
  });
  await page.goto('/login');
  await expect(page.getByRole('button', { name: 'Log in with Google' })).toBeVisible();
  await page.getByRole('button', { name: 'Log in with Google' }).click();
  const dialog = page.getByRole('dialog', { name: 'Continue to Google' });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('name, email address, profile information and Google account identifier');
  await expect(dialog).toContainText('WAOOAW does not receive your Google password');
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(dialog).toBeHidden();
  expect(providerRequests).toEqual([]);
  await attachScreenshot(page, testInfo, 'login-after-disclosure-cancel');
});

test('R-003: logout and second login request explicit Google account selection', async ({ context, page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'One clean Chromium broker-boundary journey proves the account switch contract.');
  await addSession(context, testInfo.project.name);
  await page.goto('/home');
  await page.waitForURL('**/professionals/mine');
  await page.locator('summary[aria-label="Account"]').click();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page).toHaveURL('http://127.0.0.1:3000/');
  await expect.poll(async () => context.cookies()).toEqual(expect.not.arrayContaining([
    expect.objectContaining({ name: 'next-auth.session-token' }),
  ]));

  await page.route('**/api/auth/signin/keycloak-google?**', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ url: 'http://localhost:8080/realms/waooaw/protocol/openid-connect/auth?prompt=select_account' }),
    });
  });
  await page.route('http://localhost:8080/realms/waooaw/protocol/openid-connect/auth?**', async (route) => {
    await route.fulfill({ contentType: 'text/html', body: '<title>Test identity provider</title>' });
  });
  await page.goto('/login');
  await page.getByRole('button', { name: 'Log in with Google' }).click();
  const brokerRequest = page.waitForRequest((request) => request.url().includes('/api/auth/signin/keycloak-google'));
  await page.getByRole('button', { name: 'Continue to Google' }).click();

  expect(new URL((await brokerRequest).url()).searchParams.get('prompt')).toBe('select_account');
  await expect(page).toHaveURL(/localhost:8080\/realms\/waooaw\/protocol\/openid-connect\/auth\?prompt=select_account/);
});

for (const acquisition of [
  { intent: 'trial', relationshipId: '11111111-1111-4111-8111-111111111111', displayName: 'Digital Marketing Trial' },
  { intent: 'hire', relationshipId: '22222222-2222-4222-8222-222222222222', displayName: 'Digital Marketing Hire' },
] as const) {
  test(`R-007: ${acquisition.intent} appears in My Agents without refresh`, async ({ context, page }, testInfo) => {
    test.setTimeout(60_000);
    await addSession(context, testInfo.project.name);
    const continuation = new URLSearchParams({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      version: '1.0.0',
      intent: acquisition.intent,
      disclosureRevision: '1.0.0',
      termsVersion: '2026-07-18',
      idempotencyKey: acquisition.relationshipId,
    });
    const continuationResponse = page.waitForResponse((response) => response.url().endsWith('/api/acquisition/continue'));
    await page.goto(`/marketplace?${continuation}`);
    const response = await continuationResponse;
    expect(response.ok(), await response.text()).toBe(true);
    const returnedRelationshipId = (await response.json()).relationshipId;
    await expect(page).toHaveURL(new RegExp(`/relationships/${acquisition.relationshipId}$`), { timeout: 20_000 });
    expect(returnedRelationshipId).toBe(acquisition.relationshipId);
    await page.locator('a[href="/professionals/mine"]:visible').first().click();

    await expect(page).toHaveURL(/\/professionals\/mine$/, { timeout: 20_000 });
    const acquiredAgent = page.getByRole('heading', { name: acquisition.displayName });
    await expect(acquiredAgent).toBeVisible();
    await expect(acquiredAgent.locator('xpath=ancestor::li[1]').getByRole('link', { name: 'View work' }))
      .toHaveAttribute('href', `/relationships/${acquisition.relationshipId}`);
  });
}

test('R-008 R-009 R-010 R-011 R-012 R-017 R-018: desktop shell geometry is stable', async ({ context, page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'Desktop geometry is normalized in expanded Chromium across contract widths.');
  await addSession(context, testInfo.project.name);
  for (const viewport of [{ width: 1280, height: 720 }, { width: 1440, height: 900 }, { width: 1920, height: 1080 }]) {
    await page.setViewportSize(viewport);
    await page.goto('/marketplace');
    const collapse = page.getByRole('button', { name: 'Collapse navigation' });
    if (await collapse.isVisible()) await collapse.click();
    const rail = page.locator('.side-navigation:visible').first();
    const content = page.locator('.main-content:visible').first();
    const account = page.locator('.account-drawer summary:visible').first();
    const initial = await Promise.all([rail.boundingBox(), content.boundingBox(), account.boundingBox()]);
    expect(initial[0]).toMatchObject({ x: 0, y: 0, width: 76, height: viewport.height });
    expect(initial[1]?.x).toBe(76);
    expect(initial[2]?.x).toBeGreaterThan(viewport.width - 80);
    await page.getByRole('button', { name: 'Expand navigation' }).click();
    await expect(rail).toHaveAttribute('data-expanded', 'true');
    const expanded = await Promise.all([content.boundingBox(), account.boundingBox()]);
    expect(Math.abs((expanded[0]?.x ?? 0) - (initial[1]?.x ?? 0))).toBeLessThanOrEqual(1);
    expect(Math.abs((expanded[1]?.x ?? 0) - (initial[2]?.x ?? 0))).toBeLessThanOrEqual(1);
    await expect(page.getByRole('navigation', { name: 'Customer navigation' })).toContainText('My Agents');
    await account.click();
    await expect(page.locator('.account-assurance:visible').first()).toHaveText('Account security: Verified');
    await expect(page.locator('body')).not.toContainText('AAL2_ACCOUNT');
    const headingSizes = await page.locator('h1:visible, h2:visible, h3:visible').evaluateAll((headings) => headings.map((heading) => [heading.tagName, getComputedStyle(heading).fontSize]));
    for (const [tag, size] of headingSizes) expect(size).toBe(tag === 'H1' ? '32px' : tag === 'H2' ? '24px' : '20px');
    await expectNoOverflow(page);
    await attachScreenshot(page, testInfo, `shell-${viewport.width}x${viewport.height}`);
    await page.keyboard.press('Escape');
    await expect(rail).toHaveAttribute('data-expanded', 'false');
  }
});

test('R-009 R-012: every application route preserves shell origin and typography', async ({ context, page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'The route-wide desktop matrix is normalized once at 1440x900.');
  await addSession(context, testInfo.project.name);
  for (const [name, path] of [
    ['home-destination', '/home'],
    ['marketplace', '/marketplace'],
    ['my-agents', '/professionals/mine'],
    ['alerts', '/alerts'],
    ['settings', '/settings'],
    ['profile', '/profile'],
    ['relationship', '/relationships/relationship-active'],
  ] as const) {
    await page.goto(path);
    const rail = page.locator('.side-navigation:visible');
    const content = page.locator('.main-content:visible');
    const account = page.locator('.account-drawer summary:visible');
    const collapsed = await Promise.all([content.boundingBox(), account.boundingBox()]);
    await page.getByRole('button', { name: 'Expand navigation' }).click();
    await expect(rail).toHaveAttribute('data-expanded', 'true');
    const expanded = await Promise.all([content.boundingBox(), account.boundingBox()]);
    expect(Math.abs((expanded[0]?.x ?? 0) - (collapsed[0]?.x ?? 0))).toBeLessThanOrEqual(1);
    expect(Math.abs((expanded[1]?.x ?? 0) - (collapsed[1]?.x ?? 0))).toBeLessThanOrEqual(1);
    const headingSizes = await page.locator('h1:visible, h2:visible, h3:visible').evaluateAll((headings) => headings.map((heading) => [heading.tagName, getComputedStyle(heading).fontSize]));
    for (const [tag, size] of headingSizes) expect(size).toBe(tag === 'H1' ? '32px' : tag === 'H2' ? '24px' : '20px');
    await expectNoOverflow(page);
    await attachScreenshot(page, testInfo, `route-${name}`);
    await page.keyboard.press('Escape');
    await expect(rail).toHaveAttribute('data-expanded', 'false');
  }
});

test('R-017: every supported locale survives route changes and reload', async ({ context, page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'One Chromium matrix proves all server-rendered locale cookies and directions.');
  await addSession(context, testInfo.project.name);
  await page.goto('/marketplace');
  for (const locale of supportedLocales) {
    await page.locator('.side-navigation:visible .experience-controls select').selectOption(locale);
    await expect(page.locator('html')).toHaveAttribute('lang', locale);
    await expect(page.locator('html')).toHaveAttribute('dir', locale === 'ur' ? 'rtl' : 'ltr');
    await page.goto('/alerts');
    await expect(page.locator('html')).toHaveAttribute('lang', locale);
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('lang', locale);
    await expect(page.locator('html')).toHaveAttribute('dir', locale === 'ur' ? 'rtl' : 'ltr');
    await page.goto('/marketplace');
  }
});

test('R-015: Guide is a bounded desktop pane with pointer and keyboard resize', async ({ context, page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'Desktop pane geometry is normalized once at 1440x900.');
  await addSession(context, testInfo.project.name);
  await page.goto('/marketplace');
  await page.getByRole('button', { name: 'Ask about professionals' }).first().click();
  const guide = page.getByRole('complementary', { name: 'WAOOAW Guide' });
  const separator = page.getByRole('separator', { name: 'Resize Guide' });
  await expect(guide).toBeVisible();
  expect((await guide.boundingBox())?.width).toBe(400);
  await separator.press('Home');
  expect((await guide.boundingBox())?.width).toBe(320);
  await separator.press('End');
  expect((await guide.boundingBox())?.width).toBe(560);
  const separatorBox = await separator.boundingBox();
  if (!separatorBox) throw new Error('Guide separator has no geometry');
  await separator.hover({ position: { x: 8, y: 100 } });
  await page.mouse.down();
  await page.mouse.move(separatorBox.x + 88, separatorBox.y + 100);
  await page.mouse.up();
  expect((await guide.boundingBox())?.width).toBe(480);
  const accountBox = await page.locator('.account-drawer summary').boundingBox();
  const guideBox = await guide.boundingBox();
  expect((accountBox?.x ?? 0) + (accountBox?.width ?? 0)).toBeLessThanOrEqual(guideBox?.x ?? 0);
  await attachScreenshot(page, testInfo, 'guide-desktop-pane');
});

test('R-014 R-016 R-017 R-018 R-023: compact Guide contains focus, persists truth, and restores its opener', async ({ context, page }, testInfo) => {
  await addSession(context, testInfo.project.name);
  for (const viewport of [{ width: 360, height: 800 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await context.addCookies([
      { name: 'waooaw-locale', value: 'ur', domain: '127.0.0.1', path: '/' },
      { name: 'waooaw-theme', value: 'dark', domain: '127.0.0.1', path: '/' },
    ]);
    await page.goto('/marketplace');
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
    const opener = page.locator('.conversation-launcher:visible').last();
    await opener.click();
    const guide = page.getByRole('complementary', { name: 'WAOOAW Guide' });
    await expect(guide).toBeVisible();
    const box = await guide.boundingBox();
    expect(box?.x).toBeGreaterThanOrEqual(0);
    expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(viewport.width);
    await page.getByLabel('Ask the Guide').fill('Where is my work?');
    await page.getByRole('button', { name: 'Send' }).click();
    await expect(page.getByText(/Relationship work remains with the selected professional/).last()).toBeVisible();
    await page.reload();
    await expect(page.getByText('Where is my work?').last()).toBeVisible();
    await page.locator('.conversation-close:visible').last().click();
    const currentOpener = page.locator('.conversation-launcher:visible').last();
    await currentOpener.click();
    const close = page.locator('.conversation-close:visible').last();
    const separator = page.locator('.conversation-resizer').last();
    const messageInput = page.locator('.portal-guide textarea:visible').last();
    await close.focus();
    await page.keyboard.press('Shift+Tab');
    await expect(messageInput).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(close).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(currentOpener).toBeFocused();
    await expect(page.locator('.bottom-navigation:visible').last()).toBeVisible();
    await expect(page.locator('.stop-control:visible').last()).toBeVisible();
    await currentOpener.click();
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
    for (const control of [page.locator('.portal-guide textarea:visible').last(), page.getByRole('button', { name: 'Send' }).last()]) {
      const controlBox = await control.boundingBox();
      expect(controlBox?.x).toBeGreaterThanOrEqual(0);
      expect((controlBox?.x ?? 0) + (controlBox?.width ?? 0)).toBeLessThanOrEqual(viewport.width);
      expect(controlBox?.y).toBeGreaterThanOrEqual(0);
      expect((controlBox?.y ?? 0) + (controlBox?.height ?? 0)).toBeLessThanOrEqual(viewport.height);
    }
    await expectNoOverflow(page);
    const axe = await new AxeBuilder({ page }).analyze();
    expect(axe.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
    await attachScreenshot(page, testInfo, `compact-guide-${viewport.width}x${viewport.height}`);
    await page.evaluate(() => { document.documentElement.style.fontSize = ''; });
    await page.locator('.conversation-close:visible').last().click();
    await expect(guide).toBeHidden();
  }
});