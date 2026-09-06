// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 3
// Constitutional basis: C-023 (Evidence First), C-049 (Honest Limitation), C-071 (Accessible interaction)

import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:3000';

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
  await context.addCookies([
    { name: 'waooaw-locale', value: 'en', url: baseURL },
    { name: 'waooaw-theme', value: 'light', url: baseURL },
  ]);
});

test('WC083-AUTH-01: a public auth command opens a route-backed dialog and Escape restores the portal', async ({ page }) => {
  await page.goto('/');
  const desktopLogin = page.getByRole('link', { name: 'Log in' });
  const compactRegister = page.locator('a.secondary-link[href="/register"]').first();
  const trigger = await desktopLogin.isVisible() ? desktopLogin : compactRegister;
  const dialogName = await desktopLogin.isVisible() ? 'Welcome back' : 'Create your WAOOAW account';
  await trigger.focus();
  await trigger.click();

  await expect(page).toHaveURL(/\/(login|register)$/);
  const dialog = page.getByRole('dialog', { name: dialogName });
  await expect(dialog).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Grow your business with WAOOAW AI professionals' })).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(page).toHaveURL(/\/$/);
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();
});

test('WC083-AUTH-02: backdrop dismissal returns to the originating public route', async ({ page }) => {
  await page.goto('/');
  await page.locator('a.secondary-link[href="/register"]').first().click();
  const dialog = page.getByRole('dialog', { name: 'Create your WAOOAW account' });
  await expect(dialog).toBeVisible();

  const bounds = await dialog.boundingBox();
  expect(bounds?.x).toBeGreaterThan(8);
  await page.mouse.click((bounds?.x ?? 8) - 8, bounds?.y ?? 8);

  await expect(page).toHaveURL(/\/$/);
  await expect(dialog).toHaveCount(0);
});

test('WC083-AUTH-03: direct auth routes remain standalone and provider readiness is truthful', async ({ page }) => {
  await page.goto('/login');

  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Continue with Google' })).toBeEnabled();
  await expect(page.getByRole('button', { name: /Continue with Facebook/ })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Continue with email' })).toBeEnabled();

  await page.getByRole('button', { name: 'Continue with Apple' }).click();
  await expect(page.locator('#apple-integration-status')).toContainText('Apple is coming soon');
  await expect(page).toHaveURL(/\/login$/);
});

test('WC083-AUTH-04: modal is accessible, reduced-motion safe, responsive, and RTL-aware', async ({ context, page }) => {
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
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  const bounds = await dialog.boundingBox();
  expect(bounds?.x).toBeGreaterThanOrEqual(0);
  expect((bounds?.x ?? 0) + (bounds?.width ?? 0)).toBeLessThanOrEqual(360);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  const blocking = (await new AxeBuilder({ page }).include('.auth-dialog').analyze()).violations
    .filter((violation) => violation.impact === 'critical' || violation.impact === 'serious');
  expect(blocking).toEqual([]);
});