// Implements: WC120-R013, WC120-R015, WC120-R016, WC120-R042
// Constitutional basis: C-001, C-005, C-023, C-059, C-063

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext, projectName: string) {
  const value = await encode({
    secret,
    maxAge: 60 * 60,
    token: {
      accessToken: `fixture-access-token-${projectName}`,
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 3600,
      founder: false,
      sub: `fixture-user-${projectName}`,
    },
  });
  await context.addCookies([
    { name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' },
  ]);
}

async function openConversation(page: Page) {
  await page.goto('/relationships/relationship-active');
  await page.getByRole('button', { name: 'Open conversation', exact: true }).click();
  await expect(page.getByRole('complementary', { name: 'Professional conversation' })).toHaveAttribute(
    'data-open',
    'true'
  );
}

function seriousOrCritical(results: Awaited<ReturnType<AxeBuilder['analyze']>>) {
  return results.violations.filter(({ impact }) => impact === 'serious' || impact === 'critical');
}

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('CE-FIT-10 presents consent and eligibility states accessibly', async ({ page }) => {
  await openConversation(page);
  await expect(page.getByText('Accepted by WAOOAW')).toBeVisible();
  await expect(page.getByText('Professional processing', { exact: true })).toBeVisible();
  await expect(page.getByText('Evidence pending', { exact: true })).toBeVisible();
  const stop = page.getByRole('button', { name: 'Stop all agent work now' });
  await expect(stop).toBeVisible();
  await expect(stop).toBeEnabled();
  await stop.focus();
  await expect(stop).toBeFocused();
  expect(seriousOrCritical(await new AxeBuilder({ page }).analyze())).toEqual([]);
});

test('CE-FIT-11 presents voice and media states accessibly', async ({ page }) => {
  await openConversation(page);
  const record = page.getByRole('button', { name: 'Record voice' });
  await expect(record).toBeVisible();
  await expect(record).toBeEnabled();
  await record.focus();
  await expect(record).toBeFocused();
  await expect(page.getByRole('button', { name: 'Stop all agent work now' })).toBeVisible();
  expect(seriousOrCritical(await new AxeBuilder({ page }).analyze())).toEqual([]);
});

test('CE-FIT-13 keeps Stop reachable and truthful in degraded states', async ({ page }) => {
  await openConversation(page);
  const stop = page.getByRole('button', { name: 'Stop all agent work now' });
  await expect(stop).toBeVisible();
  await stop.click();
  await expect(stop).toBeDisabled();
  await expect(stop).toContainText('Emergency Stop confirmed');
  await expect(page.locator('[aria-live="polite"]')).toContainText('Emergency Stop confirmed');
  expect(seriousOrCritical(await new AxeBuilder({ page }).analyze())).toEqual([]);
});
