// Implements: work-contracts/WC-167-acceptance-demo-readiness.md WC167-R001, WC167-R006
// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-RESP-01, §UX-SHELL-03, §UX-VIS
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import AxeBuilder from '@axe-core/playwright';
import { type BrowserContext, type Page, expect, test } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';
const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:3000';
const host = new URL(baseURL).hostname;
const subject = '8f1c2a7e-3b9d-4c55-a1f0-9a7d2c4e6b10';
const part = (value: unknown) => Buffer.from(JSON.stringify(value)).toString('base64url');
const customerToken = `${part({ alg: 'none' })}.${part({ sub: subject })}.signature`;

async function signIn(context: BrowserContext, theme: 'light' | 'dark', accessToken: string) {
  const value = await encode({
    secret,
    maxAge: 60 * 60,
    token: {
      accessToken,
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 3600,
      founder: false,
      sub: 'fixture-user',
    },
  });
  await context.clearCookies();
  await context.addCookies([
    { name: 'next-auth.session-token', value, domain: host, httpOnly: true, path: '/', sameSite: 'Lax' },
    { name: 'waooaw-locale', value: 'en', domain: host, path: '/' },
    { name: 'waooaw-theme', value: theme, domain: host, path: '/' },
  ]);
}

async function expectClean(page: Page, label: string) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(overflow, `${label} must not scroll sideways`).toBe(false);
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter(
    (violation) => violation.impact === 'critical' || violation.impact === 'serious'
  );
  expect(blocking, `${label} has serious or critical axe findings`).toEqual([]);
}

for (const theme of ['light', 'dark'] as const) {
  test(`WC167-R001 WC167-R006: /access is styled for a customer, shows the sign-in ID and passes axe (${theme})`, async ({
    context,
    page,
  }, testInfo) => {
    await signIn(context, theme, customerToken);
    await page.goto('/access');

    await expect(page.getByRole('heading', { level: 1, name: 'Staff access' })).toBeVisible();
    await expect(page.locator('.access-page > .portal-heading').first()).toBeVisible();
    await expect(page.getByText('Signed in as')).toBeVisible();
    await expect(page.getByText(subject)).toBeVisible();
    await expect(page.getByLabel('Role')).toBeVisible();
    await expect(page.getByLabel('Why do you need it?')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Send request' })).toBeDisabled();
    await expect(page.getByRole('heading', { name: 'Decide on staff access' })).toHaveCount(0);
    // The form controls take the portal control style, not the browser default.
    const radius = await page.getByLabel('Why do you need it?').evaluate((node) => getComputedStyle(node).borderRadius);
    expect(radius).not.toBe('0px');
    await expectClean(page, `/access (customer) at ${testInfo.project.name} in ${theme}`);
    await page.screenshot({ path: testInfo.outputPath(`access-customer-${theme}.png`) });
  });

  test(`WC167-R001 WC167-R006: /access and /founder/access are styled for the Founder and pass axe (${theme})`, async ({
    context,
    page,
  }, testInfo) => {
    await signIn(context, theme, 'fixture-founder-token');
    await page.goto('/access');
    await expect(page.getByRole('heading', { name: 'Decide on staff access' })).toBeVisible();
    await expect(page.getByText('ravi@example.com')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Approve' })).toBeVisible();
    await expectClean(page, `/access (Founder) at ${testInfo.project.name} in ${theme}`);

    await page.goto('/founder/access');
    await expect(page.getByRole('heading', { level: 1, name: 'Staff access' })).toBeVisible();
    await expect(page.locator('.access-page > .portal-heading').first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reject' })).toBeVisible();
    await expectClean(page, `/founder/access at ${testInfo.project.name} in ${theme}`);
    await page.screenshot({ path: testInfo.outputPath(`access-founder-${theme}.png`) });
  });
}

test('WC167-R001: the menu points at Access for a staff person, and Staff access is in everyone’s account menu', async ({
  context,
  page,
}) => {
  await signIn(context, 'light', 'fixture-founder-token');
  await page.goto('/connections');
  await expect(page.locator('#customer-navigation a[href="/access"]')).toHaveCount(1);
  await expect(page.locator('a[href="/access"]')).not.toHaveCount(0);

  await signIn(context, 'light', customerToken);
  await page.goto('/connections');
  await expect(page.locator('#customer-navigation a[href="/access"]')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Staff access', includeHidden: true }).first()).toHaveAttribute(
    'href',
    '/access'
  );
});
