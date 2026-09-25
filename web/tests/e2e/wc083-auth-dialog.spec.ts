// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 3
// Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-071 (Accessible interaction)

import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:3000';
const nextAuthSecret = 'playwright-only-not-a-runtime-secret';

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
  await context.addCookies([
    { name: 'waooaw-locale', value: 'en', url: baseURL },
    { name: 'waooaw-theme', value: 'light', url: baseURL },
  ]);
});

test('WC083-AUTH-01: a public auth command opens a route-backed dialog and Escape restores the portal', async ({
  page,
}) => {
  await page.goto('/');
  const desktopLogin = page.getByRole('link', { name: 'Log in' });
  const compactRegister = page.locator('a.secondary-link[href="/register"]').first();
  const trigger = (await desktopLogin.isVisible()) ? desktopLogin : compactRegister;
  const dialogName = (await desktopLogin.isVisible()) ? 'Log in to WAOOAW' : 'Create your WAOOAW account';
  await trigger.focus();
  await trigger.click();

  await expect(page).toHaveURL(/\/(login|register)$/);
  const dialog = page.getByRole('dialog', { name: dialogName });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('img', { name: 'WAOOAW' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Grow your business with WAOOAW AI professionals' })).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(page).toHaveURL(/\/$/);
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test('WC092-AUTH-01: login uses no preliminary dialog before the auth route resolves', async ({ page }) => {
  let releaseRoute: () => void = () => undefined;
  let markRouteRequested: () => void = () => undefined;
  const routeGate = new Promise<void>((resolve) => {
    releaseRoute = resolve;
  });
  const routeRequested = new Promise<void>((resolve) => {
    markRouteRequested = resolve;
  });
  await page.route(
    (url) => ['/login', '/register'].includes(url.pathname) && url.searchParams.has('_rsc'),
    async (route) => {
      markRouteRequested();
      await routeGate;
      await route.continue();
    }
  );
  await page.goto('/');

  const desktopLogin = page.getByRole('link', { name: 'Log in' });
  const compactRegister = page.locator('a.secondary-link[href="/register"]').first();
  const trigger = (await desktopLogin.isVisible()) ? desktopLogin : compactRegister;
  const dialogName = (await desktopLogin.isVisible()) ? 'Log in to WAOOAW' : 'Create your WAOOAW account';
  const navigation = trigger.click();
  await routeRequested;

  await expect(page.getByRole('heading', { name: 'Grow your business with WAOOAW AI professionals' })).toBeVisible();
  await expect(page.getByRole('dialog')).toHaveCount(0);

  releaseRoute();
  await navigation;
  await expect(page.getByRole('dialog', { name: dialogName })).toBeVisible();
  await page.getByRole('button', { name: 'Close' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('login loading and provider states keep identical customer-visible geometry', async ({ page }) => {
  await page.goto('/');

  const desktopLogin = page.getByRole('link', { name: 'Log in' });
  const compactRegister = page.locator('a.secondary-link[href="/register"]').first();
  const loginJourney = await desktopLogin.isVisible();
  await (loginJourney ? desktopLogin : compactRegister).click();
  const dialog = page.getByRole('dialog', {
    name: loginJourney ? 'Log in to WAOOAW' : 'Create your WAOOAW account',
  });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('Loading secure sign-in options.')).toBeVisible();
  await expect(dialog.getByText('Preparing the requested view.')).toHaveCount(0);
  const loadingBounds = await dialog.boundingBox();
  const loadingBrandBounds = await dialog.locator('.auth-brand').boundingBox();
  expect(await dialog.locator('.auth-loading-bar').evaluate((element) => getComputedStyle(element, '::after').animationName))
    .toBe('none');

  await expect(dialog.getByRole('button', { name: loginJourney ? 'Log in with Google' : 'Sign up with Google' })).toBeVisible();
  const providerControls = dialog.locator('.provider-icon-command');
  await expect(providerControls).toHaveCount(4);
  expect(await providerControls.evaluateAll((elements) => elements.map((element) => getComputedStyle(element).boxShadow)))
    .toEqual(['none', 'none', 'none', 'none']);
  const providerBorders = await providerControls.evaluateAll((elements) =>
    elements.map((element) => getComputedStyle(element).borderColor)
  );
  expect(new Set(providerBorders).size).toBe(1);
  const providerBounds = await providerControls.evaluateAll((elements) =>
    elements.map((element) => {
      const bounds = element.getBoundingClientRect();
      return { x: bounds.x, y: bounds.y };
    })
  );
  expect(providerBounds[0].y).toBeCloseTo(providerBounds[1].y, 0);
  expect(providerBounds[2].y).toBeCloseTo(providerBounds[3].y, 0);
  expect(providerBounds[0].x).toBeCloseTo(providerBounds[2].x, 0);
  expect(providerBounds[1].x).toBeCloseTo(providerBounds[3].x, 0);
  const resolvedBounds = await dialog.boundingBox();
  const resolvedBrandBounds = await dialog.locator('.auth-brand').boundingBox();

  expect(loadingBounds).not.toBeNull();
  expect(resolvedBounds).not.toBeNull();
  expect(loadingBrandBounds).not.toBeNull();
  expect(resolvedBrandBounds).not.toBeNull();
  expect(resolvedBounds?.x).toBeCloseTo(loadingBounds?.x ?? 0, 0);
  expect(resolvedBounds?.y).toBeCloseTo(loadingBounds?.y ?? 0, 0);
  expect(resolvedBounds?.width).toBeCloseTo(loadingBounds?.width ?? 0, 0);
  expect(resolvedBounds?.height).toBeCloseTo(loadingBounds?.height ?? 0, 0);
  expect(resolvedBrandBounds?.x).toBeCloseTo(loadingBrandBounds?.x ?? 0, 0);
  expect(resolvedBrandBounds?.y).toBeCloseTo(loadingBrandBounds?.y ?? 0, 0);
});

test('WC083-AUTH-02: backdrop dismissal returns to the originating public route', async ({ page }) => {
  await page.goto('/');
  await page.locator('a.secondary-link[href="/register"]').first().click();
  const dialog = page.getByRole('dialog', { name: 'Create your WAOOAW account' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('img', { name: 'WAOOAW' })).toBeVisible();
  expect(await dialog.evaluate((element) => element.scrollHeight <= element.clientHeight + 1)).toBe(true);
  await expect(dialog.getByRole('link', { name: 'Terms of Service' })).toHaveAttribute('href', '/terms');
  await expect(dialog.getByRole('link', { name: 'Privacy Policy' })).toHaveAttribute('href', '/privacy');

  const bounds = await dialog.boundingBox();
  expect(bounds?.x).toBeGreaterThan(8);
  await page.mouse.click((bounds?.x ?? 8) - 8, bounds?.y ?? 8);

  await expect(page).toHaveURL(/\/$/);
  await expect(dialog).toHaveCount(0);
});

test('WC083-AUTH-03: direct auth routes remain standalone and provider readiness is truthful', async ({ page }) => {
  await page.goto('/login');

  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Log in to WAOOAW' })).toBeVisible();
  await expect(page.getByRole('img', { name: 'WAOOAW' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Log in with Google' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Log in with Facebook' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Log in with Apple (Unavailable)' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Log in with Email (Unavailable)' })).toBeDisabled();
  await expect(page).toHaveURL(/\/login$/);
});

test('WC092-AUTH-02: policy denial offers fresh sign-in without a retry loop', async ({ context, page }, testInfo) => {
  await context.addInitScript(() => {
    if (!crypto.randomUUID) {
      Object.defineProperty(crypto, 'randomUUID', { value: () => '11111111-1111-4111-8111-111111111111' });
    }
  });
  const value = await encode({
    secret: nextAuthSecret,
    maxAge: 3600,
    token: {
      accessToken: `fixture-policy-denied-${testInfo.project.name}`,
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 3600,
      founder: false,
      sub: 'fixture-user',
    },
  });
  await context.addCookies([{ name: 'next-auth.session-token', value, httpOnly: true, sameSite: 'Lax', url: baseURL }]);

  await page.goto('/register?returnTo=%2Fsettings');

  await expect(page.getByRole('heading', { name: 'Sign in could not be completed' })).toBeVisible();
  await expect(page.getByText('We couldn’t complete your sign-in. Your account was not changed.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Try again' })).toHaveCount(0);
  await page.getByRole('button', { name: 'Sign in again' }).click();
  await expect(page).toHaveURL(/\/login\?returnTo=%2Fsettings$/);
});

test('WC083-AUTH-04: modal is accessible, reduced-motion safe, responsive, and RTL-aware', async ({
  context,
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 360, height: 800 });
  await context.addCookies([
    { name: 'waooaw-locale', value: 'ur', url: baseURL },
    { name: 'waooaw-theme', value: 'dark', url: baseURL },
  ]);
  await page.goto('/');
  await page.locator('a.secondary-link[href="/register"]').first().click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog).toHaveAccessibleName('Create your WAOOAW account');
  await expect(dialog.getByRole('img', { name: 'WAOOAW' })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  const bounds = await dialog.boundingBox();
  expect(bounds?.x).toBeGreaterThanOrEqual(0);
  expect((bounds?.x ?? 0) + (bounds?.width ?? 0)).toBeLessThanOrEqual(360);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(
    false
  );
  await page.evaluate(() => {
    document.documentElement.style.fontSize = '200%';
  });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(
    false
  );
  const signInLink = dialog.locator('a[href^="/login"]');
  await signInLink.scrollIntoViewIfNeeded();
  await expect(signInLink).toBeVisible();
  expect(await dialog.evaluate((element) => getComputedStyle(element).overflowY)).toBe('auto');
  const blocking = (await new AxeBuilder({ page }).include('.auth-dialog').analyze()).violations.filter(
    (violation) => violation.impact === 'critical' || violation.impact === 'serious'
  );
  expect(blocking).toEqual([]);
});
