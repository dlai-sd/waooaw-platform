// Implements: work-contracts/WC-096-conversational-customer-portal.md §8
// Constitutional basis: C-001, C-026, C-049, C-059, C-063

import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Page } from '@playwright/test';
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

async function expectIntegrity(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(
    true
  );
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
}

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('WC096-A04 A07: My Agents uses direct authoritative cards without document navigation or side frames', async ({
  page,
}) => {
  const documents: string[] = [];
  page.on('request', (request) => {
    if (request.resourceType() === 'document') documents.push(request.url());
  });
  await page.goto('/marketplace');
  await page.getByRole('link', { name: 'My Agents' }).first().click();

  await expect(page).toHaveURL(/\/professionals\/mine$/);
  await expect(page.getByRole('heading', { name: 'Mira' })).toBeVisible();
  await expect(page.getByText('3 enabled · 1 pending')).toBeVisible();
  await expect(page.getByText('No evidenced performance summary is available yet.')).toBeVisible();
  await expect(page.getByRole('link', { name: /View work/ })).toHaveAttribute(
    'href',
    '/relationships/relationship-active'
  );
  await expect(page.getByRole('complementary', { name: 'Getting started' })).toHaveCount(0);
  expect(documents).toHaveLength(1);
  await expectIntegrity(page);
});

test('WC096-A08 A09 A12: Guide persists across routes and relationship scope remains separate', async ({ page }) => {
  await page.goto('/marketplace');
  await page.getByRole('button', { name: 'Ask about professionals' }).first().click();
  await expect(page.getByRole('complementary', { name: 'WAOOAW Guide' })).toBeVisible();
  await page.getByLabel('Ask the Guide').fill('Where is my work?');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText(/Relationship work remains with the selected professional/)).toBeVisible();

  await page.getByRole('button', { name: 'Close conversation', exact: true }).click();
  await page.getByRole('link', { name: 'Alerts' }).first().click();
  await expect(page.getByRole('button', { name: 'Review alerts' }).first()).toBeVisible();
  await page.getByRole('button', { name: 'Review alerts' }).first().click();
  await expect(page.getByText('Where is my work?')).toBeVisible();

  await page.getByRole('button', { name: 'Close conversation', exact: true }).click();
  await page.goto('/relationships/relationship-active');
  await page.getByRole('button', { name: 'Open conversation' }).first().click();
  await expect(page.getByRole('complementary', { name: 'Professional conversation' })).toBeVisible();
  await expect(page.getByText('Where is my work?')).toHaveCount(0);
  await expect(page.getByText('Here is the current plan.')).toBeVisible();
  await expectIntegrity(page);
});

test('WC096-A06 A08 A13: compact conversation sheet and rail are keyboard accessible', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-compact-360', 'Compact geometry is normalized once at 360x800.');
  await page.goto('/professionals/mine');
  const action = page.getByRole('button', { name: 'Discuss my agents' }).first();
  await action.focus();
  await page.keyboard.press('Enter');
  const dock = page.getByRole('complementary', { name: 'WAOOAW Guide' });
  await expect(dock).toBeVisible();
  await expect
    .poll(async () => {
      const box = await dock.boundingBox();
      return Boolean(box && box.x >= 0 && box.x + box.width <= 360);
    })
    .toBe(true);
  await page.keyboard.press('Escape');
  await expect(action).toBeFocused();
  await expect(page.getByRole('navigation', { name: 'Customer mobile navigation' })).toBeVisible();
  await expectIntegrity(page);
});
