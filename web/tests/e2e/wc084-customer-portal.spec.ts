// Implements: work-contracts/WC-084-auth-readiness-and-customer-portal-plan.md §8, §12
// Constitutional basis: C-001, C-023, C-042, C-049, C-059, C-063, C-080

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext, projectName: string) {
  const value = await encode({ secret, maxAge: 3600, token: { accessToken: `fixture-access-token-${projectName}`, founder: false, sub: `fixture-user-${projectName}` } });
  await context.addCookies([{ name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' }]);
}

async function expectIntegrity(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
}

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('WC084-PORTAL-01: customer can navigate server-owned portal summaries', async ({ page }) => {
  await page.goto('/home');
  await expect(page.getByRole('heading', { name: 'My Agents' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Mira' })).toBeVisible();
  await expectIntegrity(page);

  await page.goto('/marketplace');
  await expect(page.getByRole('heading', { name: 'Digital Marketing Professional' })).toBeVisible();
  await expect(page.getByText('₹1,180.00')).toBeVisible();
  await page.getByRole('link', { name: 'Review trial disclosure' }).click();
  await expect(page).toHaveURL(/\/professionals\/digital-marketing$/);
  await expect(page.getByRole('heading', { name: 'Digital Marketing Professional' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Start the approved registration path' })).toBeVisible();
  await expectIntegrity(page);

  await page.goto('/alerts');
  await expect(page.getByText('actionable')).toBeVisible();
  await expect(page.getByText('informational')).toBeVisible();
  await expect(page.getByText(/does not approve or complete/)).toBeVisible();
  await page.getByRole('button', { name: 'Acknowledge' }).click();
  await expect(page.getByText('acknowledged')).toBeVisible();
  await expectIntegrity(page);
});

test('WC084-PORTAL-02: profile and settings expose owned truth and Billing limitation', async ({ page }) => {
  await page.goto('/profile');
  await expect(page.getByLabel('Display name')).toHaveValue('Asha Rao');
  await expect(page.getByText(/customer-global WBE projection is not yet supplied/)).toBeVisible();
  await page.getByLabel('Display name').fill('Asha Rao Updated');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page.getByText('Profile saved.')).toBeVisible();
  await page.goto('/settings');
  await expect(page.getByLabel('Locale')).toHaveValue('en-IN');
  await expect(page.getByText('web, email')).toBeVisible();
  await page.getByRole('button', { name: 'Save settings' }).click();
  await expect(page.getByText('Settings saved.')).toBeVisible();
  await page.getByLabel('Account', { exact: true }).click();
  await expect(page.getByRole('link', { name: 'Billing' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
  await expectIntegrity(page);
});

test('WC084-PORTAL-03: relationship lifecycle remains goal-gated with Stop visible', async ({ page }) => {
  await page.goto('/relationships/relationship-active');
  await expect(page.getByRole('heading', { name: 'From configuration to operations' })).toBeVisible();
  await expect(page.getByText('Goal Verification', { exact: true })).toBeVisible();
  await expect(page.getByText('Customer goal verification is required.')).toBeVisible();
  await expect(page.getByText(/no canonical verification command exists/)).toBeVisible();
  await page.getByLabel('Agent display name').fill('Mira');
  await page.getByRole('button', { name: 'Save Onboard preferences' }).click();
  await expect(page.getByText('Onboard preferences saved.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Emergency Stop' })).toBeVisible();
  await expectIntegrity(page);
});

test('WC084-PORTAL-04: compact RTL and 200 percent reflow preserve navigation', async ({ context, page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('chromium'), 'Reflow is covered once on Chromium projects.');
  await context.addCookies([{ name: 'waooaw-locale', value: 'ur', domain: '127.0.0.1', path: '/' }]);
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/home');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
  await expect(page.locator('nav.bottom-navigation')).toBeVisible();
  await expectIntegrity(page);
});