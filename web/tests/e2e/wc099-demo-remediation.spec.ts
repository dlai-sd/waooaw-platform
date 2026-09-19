// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md R-001–R-018, R-020, R-023, R-029–R-032
// Constitutional basis: C-001, C-023, C-049, C-059, C-063

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Locator, type Page, type TestInfo } from '@playwright/test';
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

async function expectPortalTypography(page: Page) {
  const metrics = await page.locator('.app-shell-customer:visible').evaluate((shell) => {
    const visibleText = [...shell.querySelectorAll<HTMLElement>('*')].filter((element) => {
      const hasDirectText = [...element.childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent?.trim());
      const bounds = element.getBoundingClientRect();
      return hasDirectText && bounds.width > 0 && bounds.height > 0;
    });
    const body = visibleText.find((element) => !element.closest('h1, h2, h3'));
    const title = visibleText.find((element) => element.closest('h1, h2, h3'));
    const content = shell.querySelector<HTMLElement>('.portal-page, .workspace-shell, .content-page, .state-view');
    if (!body || !title || !content) throw new Error('Portal typography evidence target is missing.');
    return {
      bodySize: Number.parseFloat(getComputedStyle(body).fontSize),
      titleSize: Number.parseFloat(getComputedStyle(title).fontSize),
      sizes: [...new Set(visibleText.map((element) => Number.parseFloat(getComputedStyle(element).fontSize)))],
      letterSpacing: [...new Set(visibleText.map((element) => {
        const spacing = getComputedStyle(element).letterSpacing;
        return spacing === 'normal' ? 0 : Number.parseFloat(spacing);
      }))],
      topPadding: Number.parseFloat(getComputedStyle(content).paddingTop),
    };
  });
  expect(metrics.sizes).toEqual(expect.arrayContaining([metrics.bodySize, metrics.titleSize]));
  expect(metrics.sizes).toHaveLength(2);
  expect(metrics.titleSize - metrics.bodySize).toBeCloseTo(2 * 96 / 72, 2);
  expect(metrics.letterSpacing).toEqual([0]);
  expect(metrics.topPadding).toBeCloseTo(metrics.bodySize, 2);
}

async function expectCardGrid(cards: Locator, columns: 1 | 2) {
  await expect.poll(() => cards.count()).toBeGreaterThanOrEqual(2);
  const boxes = await cards.evaluateAll((items) => items.map((item) => {
    const bounds = item.getBoundingClientRect();
    return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height, viewportWidth: document.documentElement.clientWidth, contentFits: item.scrollHeight <= item.clientHeight + 1 };
  }));
  expect(boxes.every(({ x, width, viewportWidth, contentFits }) => x >= 0 && x + width <= viewportWidth && contentFits)).toBe(true);
  if (columns === 2) {
    for (let index = 0; index < boxes.length; index += 2) {
      if (boxes[index + 1]) expect(Math.abs(boxes[index].y - boxes[index + 1].y)).toBeLessThanOrEqual(1);
    }
  } else {
    expect(boxes.every((box) => Math.abs(box.x - boxes[0].x) <= 1)).toBe(true);
  }
}

function expectNoIntersection(first: { x: number; y: number; width: number; height: number }, second: { x: number; y: number; width: number; height: number }) {
  expect(first.x + first.width <= second.x || second.x + second.width <= first.x
    || first.y + first.height <= second.y || second.y + second.height <= first.y).toBe(true);
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
  await page.locator('summary[aria-label="Account"]').first().click();
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

for (const intent of ['trial', 'hire'] as const) {
  test(`R-003 R-005 R-006: stale registration authentication reauthenticates without losing ${intent} intent`, async ({ context, page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-expanded', 'One Chromium broker-boundary journey per acquisition intent proves fresh-auth continuation parameters.');
    const acquisitionTarget = `/marketplace?professionalType=DIGITAL_MARKETING&version=3.1.0&intent=${intent}`;
    await addSession(context, testInfo.project.name);
    await page.route('**/api/identity/registration', async (route) => route.fulfill({
      status: 403,
      contentType: 'application/json',
      body: JSON.stringify({ code: 'IDENTITY_STEP_UP_REQUIRED' }),
    }));
    await page.route('**/api/auth/signin/keycloak-google?**', async (route) => route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ url: 'http://localhost:8080/realms/waooaw/protocol/openid-connect/auth?prompt=select_account&max_age=0' }),
    }));
    await page.route('http://localhost:8080/realms/waooaw/protocol/openid-connect/auth?**', async (route) => {
      await route.fulfill({ contentType: 'text/html', body: '<title>Test identity provider</title>' });
    });

    await page.goto(`/register?returnTo=${encodeURIComponent(acquisitionTarget)}`);
    await expect(page.getByText('For your security, sign in again to continue. Your account was not changed.')).toBeVisible();
    const brokerRequest = page.waitForRequest((request) => request.url().includes('/api/auth/signin/keycloak-google'));
    await page.getByRole('button', { name: 'Continue securely' }).click();

    const request = await brokerRequest;
    const requestUrl = new URL(request.url());
    expect(requestUrl.searchParams.get('prompt')).toBe('select_account');
    expect(requestUrl.searchParams.get('max_age')).toBe('0');
    expect(new URLSearchParams(request.postData() ?? '').get('callbackUrl'))
      .toBe(`/register?returnTo=${encodeURIComponent(acquisitionTarget)}`);
    await expect(page).toHaveURL(/localhost:8080\/realms\/waooaw\/protocol\/openid-connect\/auth\?prompt=select_account&max_age=0/);
  });
}

test('R-010: account menu dismisses outside and on Escape while restoring focus', async ({ context, page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'One Chromium interaction journey proves native account-menu dismissal.');
  await addSession(context, testInfo.project.name);
  await page.goto('/marketplace');
  const account = page.locator('summary[aria-label="Account"]').first();
  const drawer = page.locator('details.account-drawer').first();

  await account.click();
  await expect(drawer).toHaveAttribute('open', '');
  await page.mouse.click(400, 400);
  await expect(drawer).not.toHaveAttribute('open', '');

  await account.click();
  await page.keyboard.press('Escape');
  await expect(drawer).not.toHaveAttribute('open', '');
  await expect(account).toBeFocused();
});

for (const acquisition of [
  { intent: 'trial', relationshipId: '11111111-1111-4111-8111-111111111111', displayName: 'Digital Marketing Trial' },
  { intent: 'hire', relationshipId: '22222222-2222-4222-8222-222222222222', displayName: 'Digital Marketing Hire' },
] as const) {
  test(`R-007: ${acquisition.intent} appears in My Agents without refresh`, async ({ context, page }, testInfo) => {
    test.setTimeout(60_000);
    await addSession(context, testInfo.project.name);
    await page.goto('/marketplace');
    const result = await page.evaluate(async (body) => {
      const response = await fetch('/api/acquisition/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      return { ok: response.ok, status: response.status, body: await response.json() as { relationshipId?: string } };
    }, {
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      professionalVersion: '1.0.0',
      intent: acquisition.intent,
      disclosureRevision: '1.0.0',
      termsVersion: '2026-07-18',
      idempotencyKey: acquisition.relationshipId,
    });
    expect(result.ok, JSON.stringify(result.body)).toBe(true);
    expect(result.body.relationshipId).toBe(acquisition.relationshipId);
    await page.goto('/professionals/mine');

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
    await expectPortalTypography(page);
    await expect(page.getByRole('search')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Apply' })).toHaveCount(0);
    await expectCardGrid(page.locator('section[aria-labelledby="marketplace-title"]:visible').first().locator('.marketplace-grid > li'), 2);
    const launcherBox = await page.locator('.conversation-launcher:visible').boundingBox();
    const stopBox = await page.locator('.stop-control:visible').boundingBox();
    if (!launcherBox || !stopBox) throw new Error('Persistent control geometry is missing.');
    expectNoIntersection(launcherBox, stopBox);
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
    await expectPortalTypography(page);
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

test('R-031 R-032: Marketplace and My Agents keep complete two-column and narrow single-column cards', async ({ context, page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'One Chromium viewport matrix proves the responsive card contract.');
  await addSession(context, testInfo.project.name);
  for (const viewport of [
    { width: 1280, height: 720, columns: 2 as const },
    { width: 1440, height: 900, columns: 2 as const },
    { width: 360, height: 800, columns: 1 as const },
    { width: 390, height: 844, columns: 1 as const },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto('/marketplace');
    const marketplace = page.locator('section[aria-labelledby="marketplace-title"]:visible').first();
    await expect(page.getByRole('search')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Apply' })).toHaveCount(0);
    expect(await marketplace.locator('.marketplace-heading').evaluate((element) => getComputedStyle(element).borderBottomWidth)).toBe('0px');
    await expectCardGrid(marketplace.locator('.marketplace-grid > li'), viewport.columns);
    await expectPortalTypography(page);
    await expectNoOverflow(page);
    await attachScreenshot(page, testInfo, `marketplace-grid-${viewport.width}x${viewport.height}`);

    await page.goto('/professionals/mine');
    const myAgents = page.locator('section[aria-labelledby="my-experts-title"]:visible').first();
    await expectCardGrid(myAgents.locator('.agent-dashboard > li'), viewport.columns);
    await expectPortalTypography(page);
    await expectNoOverflow(page);
    await attachScreenshot(page, testInfo, `my-agents-grid-${viewport.width}x${viewport.height}`);
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
  await expect(page.locator('.conversation-launcher')).toHaveCount(0);
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
  const stopBox = await page.locator('.stop-control:visible').boundingBox();
  expect((accountBox?.x ?? 0) + (accountBox?.width ?? 0)).toBeLessThanOrEqual(guideBox?.x ?? 0);
  if (!guideBox || !stopBox) throw new Error('Guide control geometry is missing.');
  expectNoIntersection(guideBox, stopBox);
  await attachScreenshot(page, testInfo, 'guide-desktop-pane');
});

test('R-014 R-016 R-017 R-018 R-023: compact Guide contains focus, persists truth, and restores its opener', async ({ context, page }, testInfo) => {
  await addSession(context, testInfo.project.name);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const testCase of [
    { viewport: { width: 360, height: 800 }, locale: 'hi', message: '\u092e\u0947\u0930\u0947 \u0921\u093f\u091c\u093f\u091f\u0932 \u092a\u0947\u0936\u0947\u0935\u0930 \u0915\u093e \u0915\u093e\u092e \u0914\u0930 \u0905\u0917\u0932\u0947 \u0938\u0924\u094d\u092f\u093e\u092a\u0928 \u0915\u0947 \u0915\u0926\u092e \u0915\u0939\u093e\u0902 \u0926\u093f\u0916\u093e\u0908 \u0926\u0947\u0902\u0917\u0947?' },
    { viewport: { width: 390, height: 844 }, locale: 'ur', message: '\u0645\u06cc\u0631\u06d2 \u0688\u062c\u06cc\u0679\u0644 \u067e\u06cc\u0634\u06c1 \u0648\u0631 \u06a9\u0627 \u06a9\u0627\u0645 \u0627\u0648\u0631 \u0627\u06af\u0644\u06d2 \u062a\u0635\u062f\u06cc\u0642\u06cc \u0645\u0631\u0627\u062d\u0644 \u06a9\u06c1\u0627\u06ba \u0646\u0638\u0631 \u0622\u0626\u06cc\u06ba \u06af\u06d2\u061f' },
    { viewport: { width: 768, height: 1024 }, locale: 'en', message: 'Where can I review my professional work and the next verification steps?' },
  ] as const) {
    const { viewport, locale, message } = testCase;
    await page.setViewportSize(viewport);
    await context.addCookies([
      { name: 'waooaw-locale', value: locale, domain: '127.0.0.1', path: '/' },
      { name: 'waooaw-theme', value: 'dark', domain: '127.0.0.1', path: '/' },
    ]);
    await page.goto('/marketplace');
    await expect(page.locator('html')).toHaveAttribute('lang', locale);
    await expect(page.locator('html')).toHaveAttribute('dir', locale === 'ur' ? 'rtl' : 'ltr');
    const opener = page.locator('.conversation-launcher:visible').last();
    await opener.click();
    const guide = page.getByRole('complementary', { name: 'WAOOAW Guide' });
    await expect(guide).toBeVisible();
    await expect(page.locator('.conversation-launcher')).toHaveCount(0);
    const box = await guide.boundingBox();
    expect(box?.x).toBeGreaterThanOrEqual(0);
    expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(viewport.width);
    await page.getByLabel('Ask the Guide').fill(message);
    await page.getByRole('button', { name: 'Send' }).click();
    await expect(page.getByText(/Relationship work remains with the selected professional/).last()).toBeVisible();
    await page.reload();
    await expect(page.getByText(message).last()).toBeVisible();
    await page.locator('.conversation-close:visible').last().click();
    const currentOpener = page.locator('.conversation-launcher:visible').last();
    await currentOpener.click();
    const separator = page.locator('.conversation-resizer').last();
    const messageInput = page.locator('.portal-guide textarea:visible').last();
    await separator.focus();
    await page.keyboard.press('Shift+Tab');
    await expect(messageInput).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(currentOpener).toBeFocused();
    await expect(page.locator(viewport.width < 768 ? '.bottom-navigation:visible' : '.side-navigation:visible').last()).toBeVisible();
    await expect(page.locator('.stop-control:visible').last()).toBeVisible();
    const closedLauncherBox = await currentOpener.boundingBox();
    const closedStopBox = await page.locator('.stop-control:visible').last().boundingBox();
    if (!closedLauncherBox || !closedStopBox) throw new Error('Compact persistent control geometry is missing.');
    expectNoIntersection(closedLauncherBox, closedStopBox);
    await currentOpener.click();
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
    if (viewport.width === 360 && testInfo.project.name.startsWith('chromium')) {
      await page.route('**/api/interactions/portal', async (route) => {
        if (route.request().method() === 'POST') await route.fulfill({ status: 503, body: '{}' });
        else await route.continue();
      });
      await page.getByLabel('Ask the Guide').fill('Show a recoverable Guide failure');
      await page.getByRole('button', { name: 'Send' }).click();
      await expect(page.locator('.conversation-error[role="alert"]')).toHaveText('The Guide response is unresolved. Refresh before retrying.');
    }
    for (const control of [page.locator('.portal-guide textarea:visible').last(), page.getByRole('button', { name: 'Send' }).last(), page.locator('.conversation-error[role="alert"]')]) {
      if (await control.count() === 0) continue;
      const controlBox = await control.boundingBox();
      expect(controlBox?.x).toBeGreaterThanOrEqual(0);
      expect((controlBox?.x ?? 0) + (controlBox?.width ?? 0)).toBeLessThanOrEqual(viewport.width);
      expect(controlBox?.y).toBeGreaterThanOrEqual(0);
      expect((controlBox?.y ?? 0) + (controlBox?.height ?? 0)).toBeLessThanOrEqual(viewport.height);
    }
    const timeline = page.locator('.portal-guide-timeline:visible').last();
    const composer = page.locator('.portal-guide form:visible').last();
    expect(await timeline.evaluate((element) => getComputedStyle(element).overflowY)).toBe('auto');
    expect(await composer.evaluate((element) => element.parentElement?.classList.contains('portal-guide'))).toBe(true);
    await expectNoOverflow(page);
    const axe = await new AxeBuilder({ page }).analyze();
    expect(axe.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
    await attachScreenshot(page, testInfo, `compact-guide-${viewport.width}x${viewport.height}`);
    await page.unroute('**/api/interactions/portal');
    await page.evaluate(() => { document.documentElement.style.fontSize = ''; });
    await page.locator('.conversation-close:visible').last().click();
    await expect(guide).toBeHidden();
  }
});