// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-AUTH-01–06, §UX-PRIV-01, §UX-PWA-04
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext) {
  const value = await encode({ secret, maxAge: 60 * 60, token: { accessToken: 'fixture-access-token', founder: false, sub: 'fixture-user' } });
  await context.addCookies([{ name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' }]);
}

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
  await context.addCookies([{ name: 'waooaw-locale', value: 'en', domain: '127.0.0.1', path: '/' }]);
});

test('UX-AUTH-01 UX-PRIV-01: registration is broker-gated and the browser session contains no bearer token', async ({ context, page }) => {
  await page.goto('/register');
  await expect(page.getByRole('button', { name: /Continue securely/ })).toBeVisible();
  await expect(page.getByLabel('Your name')).toHaveCount(0);

  await addSession(context);
  const browserSession = await page.request.get('/api/auth/session');
  const sessionBody = await browserSession.text();
  expect(JSON.parse(sessionBody)).toMatchObject({ authenticated: true, founder: false });
  expect(sessionBody).not.toContain('fixture-access-token');
});

test('UX-AUTH-02 UX-AUTH-06 UX-PWA-04: verified broker state renders a private, responsive registration step', async ({ context, page }) => {
  await addSession(context);
  await page.route('**/api/identity/registration', async (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      registrationId: '8f6f7550-98c7-4a8f-bd63-36f07ee15c9d', state: 'PROFILE_COMPLETION_REQUIRED', nextAction: 'COMPLETE_PROFILE',
      authenticationPath: 'GOOGLE', emailVerified: true, mobileVerified: false, profile: {}, expiresAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
    }),
  }));
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/register');
  await expect(page.getByLabel('Your name')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save and continue' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  expect((await new AxeBuilder({ page }).analyze()).violations.filter((violation) => violation.impact === 'critical' || violation.impact === 'serious')).toEqual([]);

  await expect(page.getByRole('button', { name: 'Switch account' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
});