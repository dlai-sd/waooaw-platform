// Implements: work-contracts/WC-094-demo-auth-session-readiness-repair.md WC094-A01, WC094-A03
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { expect, test, type BrowserContext } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:3000';
const nextAuthSecret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext) {
  const value = await encode({
    secret: nextAuthSecret,
    maxAge: 3600,
    token: {
      accessToken: 'fixture-access-token',
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 3600,
      founder: false,
      idToken: 'fixture-id-token',
      sub: 'fixture-user',
    },
  });
  await context.addCookies([
    { name: 'next-auth.session-token', value, httpOnly: true, sameSite: 'Lax', url: baseURL },
    { name: 'waooaw-theme', value: 'dark', sameSite: 'Lax', url: baseURL },
  ]);
}

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
  await context.addCookies([{ name: 'waooaw-locale', value: 'en', sameSite: 'Lax', url: baseURL }]);
});

test('WC094-A03: Login and Register project the same available brokers', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByRole('button', { name: 'Log in with Google' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Log in with Facebook' })).toBeEnabled();

  await page.goto('/register');
  await expect(page.getByRole('button', { name: 'Sign up with Google' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Sign up with Facebook' })).toBeEnabled();
});

test('WC094-A01: logout clears WAOOAW state and returns through Keycloak to the homepage', async ({ context, page }) => {
  await addSession(context);
  let logoutContinuationStatus: number | undefined;
  page.on('response', (response) => {
    const url = new URL(response.url());
    if (url.pathname === '/api/auth/keycloak-logout' && url.searchParams.has('nonce')) {
      logoutContinuationStatus = response.status();
    }
  });
  await page.goto('/home');
  await page.waitForURL('**/professionals/mine');
  await page.evaluate(() => {
    localStorage.setItem('waooaw:conversation:relationship-a:draft', 'protected draft');
    sessionStorage.setItem('waooaw:identity:registration-draft', 'protected registration');
    localStorage.setItem('unrelated-preference', 'preserve');
  });

  await page.locator('summary[aria-label="Account"]').first().click();
  await page.getByRole('button', { name: 'Sign out' }).click();

  await expect.poll(() => logoutContinuationStatus).toBe(303);
  await expect(page).toHaveURL(`${baseURL}/`);
  await expect(page.getByRole('heading', { name: 'Grow your business with WAOOAW AI professionals' })).toBeVisible();
  await expect.poll(async () => context.cookies()).toEqual(expect.not.arrayContaining([
    expect.objectContaining({ name: 'next-auth.session-token' }),
    expect.objectContaining({ name: 'waooaw-theme' }),
  ]));
  await expect.poll(() => page.evaluate(() => ({
    localWaaoawKeys: Object.keys(localStorage).filter((key) => key.startsWith('waooaw:')),
    sessionWaaoawKeys: Object.keys(sessionStorage).filter((key) => key.startsWith('waooaw:')),
    unrelated: localStorage.getItem('unrelated-preference'),
  }))).toEqual({ localWaaoawKeys: [], sessionWaaoawKeys: [], unrelated: 'preserve' });
});
