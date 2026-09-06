// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 3
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability)

import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:3000';
const evidenceDir = path.resolve(process.env.WC083_EVIDENCE_DIR ?? '../test-results/wc083');
const screenshotDir = path.join(evidenceDir, 'screenshots');

async function setPreferences(page: Page, locale: 'en' | 'ur', theme: 'light' | 'dark') {
  await page.context().clearCookies();
  await page.context().addCookies([
    { name: 'waooaw-locale', value: locale, url: baseURL },
    { name: 'waooaw-theme', value: theme, url: baseURL },
  ]);
}

async function dismissConsent(page: Page) {
  const reject = page.getByRole('button', { name: 'Reject optional' });
  if (await reject.isVisible()) await reject.click();
}

test.beforeAll(async () => mkdir(screenshotDir, { recursive: true }));

test('WC083-VIS-01: capture reviewed authentication states', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await setPreferences(page, 'en', 'light');
  await page.goto('/');
  await dismissConsent(page);
  await page.getByRole('link', { name: 'Log in' }).click();
  await expect(page.getByRole('dialog', { name: 'Welcome back' })).toBeVisible();
  await page.screenshot({ animations: 'disabled', path: path.join(screenshotDir, 'login-desktop-light.png') });

  await page.keyboard.press('Escape');
  await setPreferences(page, 'en', 'dark');
  await page.reload();
  await page.locator('a.secondary-link[href="/register"]').first().click();
  await expect(page.getByRole('dialog', { name: 'Create your WAOOAW account' })).toBeVisible();
  await page.screenshot({ animations: 'disabled', path: path.join(screenshotDir, 'register-desktop-dark.png') });

  await page.keyboard.press('Escape');
  await page.setViewportSize({ width: 360, height: 800 });
  await setPreferences(page, 'ur', 'dark');
  await page.reload();
  await page.locator('a.secondary-link[href="/register"]').first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.screenshot({ animations: 'disabled', path: path.join(screenshotDir, 'register-mobile-rtl-dark.png') });

  await page.keyboard.press('Escape');
  await page.setViewportSize({ width: 768, height: 1024 });
  await setPreferences(page, 'en', 'light');
  await page.reload();
  await page.locator('a.secondary-link[href="/register"]').first().click();
  await page.getByRole('button', { name: 'Continue with Apple' }).click();
  await expect(page.locator('#apple-integration-status')).toBeVisible();
  await page.screenshot({ animations: 'disabled', path: path.join(screenshotDir, 'apple-placeholder-intermediate.png') });
});