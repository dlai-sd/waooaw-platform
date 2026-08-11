// Implements: WC-034 F4 Relationship Workspace browser acceptance
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext, projectName: string) {
  const value = await encode({ secret, maxAge: 3600, token: { accessToken: `fixture-access-token-${projectName}`, founder: false, sub: `fixture-user-${projectName}` } });
  await context.addCookies([{ name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' }]);
}

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('F4 workspace exposes all mandatory views without hiding Stop or overflowing', async ({ page }, testInfo) => {
  test.skip(!['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name), 'Required F4 viewports only.');
  await page.goto('/relationships/relationship-active');

  const workspaceNavigation = page.getByRole('navigation', { name: 'Relationship workspace views' });
  for (const name of ['Plan', 'Needs your attention', 'Work', 'Results', 'Usage & budget', 'Rights & control']) {
    await expect(workspaceNavigation.getByRole('link', { name, exact: true })).toBeVisible();
  }
  await expect(page.getByText('Nothing currently requires your response.')).toBeVisible();
  await expect(page.getByText('No supported business outcome is available yet.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Emergency Stop' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
});