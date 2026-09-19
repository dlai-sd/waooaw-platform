// Implements: WC-034 F4 Relationship Workspace browser acceptance
// Constitutional basis: C-001, C-005, C-023, C-026, C-059, C-063

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext, projectName: string) {
  const value = await encode({
    secret,
    maxAge: 3600,
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

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('F4 workspace exposes all mandatory views without hiding Stop or overflowing', async ({ page }, testInfo) => {
  test.skip(
    !['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name),
    'Required F4 viewports only.'
  );
  await page.goto('/relationships/relationship-active');

  const workspaceNavigation = page.getByRole('navigation', { name: 'Relationship workspace views' });
  for (const name of ['Plan', 'Needs your attention', 'Work', 'Results', 'Usage & budget', 'Rights & control']) {
    await expect(workspaceNavigation.getByRole('link', { name, exact: true })).toBeVisible();
  }
  await expect(page.getByText('Nothing currently requires your response.')).toBeVisible();
  await expect(page.getByText('No supported business outcome is available yet.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Emergency Stop' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(
    true
  );
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
});

test('WC059 contract choices remain symmetric, responsive, and accessible', async ({ page }, testInfo) => {
  test.skip(
    !['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name),
    'Required WC059 viewports only.'
  );
  await page.goto('/relationships/relationship-contract');

  await expect(page.getByRole('heading', { name: 'Employment contract' })).toBeVisible();
  await expect(page.locator('.contract-money dd').filter({ hasText: '₹1,180.00' }).first()).toBeVisible();
  const decisions = page.getByRole('group', { name: 'Contract decisions' });
  for (const name of ['Hire and accept exact contract', 'Not now', 'Cancel', 'Exit'])
    await expect(decisions.getByRole(name === 'Exit' ? 'link' : 'button', { name })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Emergency Stop' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(
    true
  );
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
});

test('WC095 responsive lifecycle keeps review blockers, actions, and Stop reachable at 200 percent text', async ({
  page,
}, testInfo) => {
  test.skip(
    !['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name),
    'Required WC095 viewports only.'
  );
  await page.goto('/relationships/relationship-active');
  await page.evaluate(() => {
    document.documentElement.style.fontSize = '200%';
  });

  const performance = page.getByRole('heading', { name: 'Performance' }).locator('..');
  await expect(performance.getByText(/Attribution limit: No causal guarantee/).first()).toBeVisible();
  await expect(performance.getByText(/affected work remains locked/).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Record review decision' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Emergency Stop' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(
    true
  );

  const decision = page.getByRole('combobox', { name: 'Decision', exact: true });
  await decision.focus();
  await page.keyboard.press('End');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('textbox', { name: 'Reason', exact: true })).toBeFocused();
  await page.keyboard.type('Customer requests a governed reassessment.');
  await page.keyboard.press('Tab');
  await page.keyboard.press('Enter');
  await expect(page.getByText(/Review decision recorded/)).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
});

test('WC095 relationship switching and refresh reconstruct only selected relationship review state', async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== 'chromium-expanded',
    'One browser proves server reconstruction and relationship isolation.'
  );
  await page.goto('/relationships/relationship-active');
  await expect(page.locator('.lifecycle-details p').filter({ hasText: 'MARKET_RESEARCH ·' }).first()).toBeVisible();
  await page.getByRole('link', { name: 'Arun' }).click();
  await expect(page).toHaveURL(/\/relationships\/relationship-second$/);
  await expect(page.locator('.lifecycle-details p').filter({ hasText: 'TUTORING_PLAN ·' }).first()).toBeVisible();
  await expect(page.locator('.lifecycle-details p').filter({ hasText: 'MARKET_RESEARCH ·' })).toHaveCount(0);
  await page.reload();
  await expect(page.locator('.lifecycle-details p').filter({ hasText: 'TUTORING_PLAN ·' }).first()).toBeVisible();
  await expect(page.getByRole('link', { name: 'Arun' })).toHaveAttribute('aria-current', 'page');
});

test('WC095 payable checkout fails closed without Razorpay configuration and collects no credentials', async ({
  page,
}, testInfo) => {
  test.skip(
    !['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name),
    'Required WC095 viewports only.'
  );
  await page.goto('/relationships/relationship-contract');
  await page.getByRole('button', { name: 'Hire and accept exact contract' }).click();
  await page.getByRole('button', { name: 'Continue to payment' }).click();
  await expect(page.locator('.decision-status')).toContainText(
    'Razorpay configuration is pending. No payment was started.'
  );
  await expect(page.getByText(/Payment details are entered only on Razorpay/)).toBeVisible();
  await expect(page.locator('.contract-journey input, .contract-journey iframe')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Emergency Stop' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(
    true
  );
});

test('WC095 fully discounted checkout discloses all method families as not required', async ({ page }, testInfo) => {
  test.skip(
    !['chromium-expanded', 'chromium-compact-360'].includes(testInfo.project.name),
    'Required WC095 viewports only.'
  );
  await page.goto('/relationships/relationship-discounted');
  await page.getByRole('button', { name: 'Hire and accept exact contract' }).click();
  await page.getByRole('button', { name: 'Continue to payment' }).click();
  await expect(page.getByText('Amount paid', { exact: true }).locator('..')).toContainText('INR 0');
  const methods = page.getByRole('list', { name: 'Payment methods not required' });
  for (const method of ['Credit card', 'Debit card', 'UPI', 'Netbanking', 'Wallet']) {
    await expect(methods.getByText(method, { exact: true })).toBeVisible();
  }
  await expect(methods.getByText(/Not required - 100% Demo discount applied/)).toHaveCount(5);
  await expect(page.locator('.contract-journey input, .contract-journey iframe')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(
    true
  );
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
});
