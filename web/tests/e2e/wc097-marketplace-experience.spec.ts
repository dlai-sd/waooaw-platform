// Implements: work-contracts/WC-097-marketplace-acquisition-experience.md A01-A07
// Constitutional basis: C-023, C-049, C-059

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
  const overflow = await page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    if (document.documentElement.scrollWidth <= viewportWidth) return [];
    return [...document.querySelectorAll<HTMLElement>('body *')]
      .filter((element) => {
        const bounds = element.getBoundingClientRect();
        return (
          getComputedStyle(element).visibility !== 'hidden' && (bounds.right > viewportWidth + 1 || bounds.left < -1)
        );
      })
      .map((element) => ({
        className: element.className,
        left: element.getBoundingClientRect().left,
        right: element.getBoundingClientRect().right,
        tagName: element.tagName,
      }));
  });
  expect(overflow, 'elements must remain within the viewport').toEqual([]);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')).toEqual([]);
  if ((page.viewportSize()?.width ?? 0) <= 599) {
    await expect(page.locator('.conversation-launcher')).toBeHidden();
    await expect(page.getByRole('button', { name: 'Ask about professionals' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'No active work to stop' })).toHaveCount(0);
  }
}

async function expectShellReady(page: Page) {
  await page.getByRole('button', { name: 'Expand navigation' }).click();
  await expect(page.getByRole('button', { name: 'Collapse navigation' })).toBeVisible();
  await page.getByRole('button', { name: 'Collapse navigation' }).click();
  await expect(page.getByRole('button', { name: 'Expand navigation' })).toBeVisible();
}

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('WC097-A01-A07: professional offer stays in the customer shell through Trial review', async ({
  page,
}, testInfo) => {
  const documents: string[] = [];
  page.on('request', (request) => {
    if (request.resourceType() === 'document') documents.push(request.url());
  });
  await page.goto('/marketplace');
  await expectShellReady(page);

  const shell = page.locator('.app-shell-customer:visible');
  await expect(shell).toBeVisible();
  const shellElement = await shell.elementHandle();
  await expect(page.getByRole('heading', { name: 'Digital Marketing Professional' })).toBeVisible();
  await expect(
    page.getByText('Builds evidence-backed digital marketing plans for lawful local service businesses.')
  ).toBeVisible();
  await expect(page.getByText('DIGITAL_MARKETING_LOCAL_SERVICE')).toHaveCount(0);
  await expect(page.getByText(/Eligibility depends only/)).toHaveCount(0);
  await expect(page.getByRole('link', { name: /Hire/ }).first()).toHaveAttribute('href', /intent=hire/);
  await page.screenshot({ path: testInfo.outputPath('marketplace-card.png'), fullPage: true });

  await page
    .getByRole('link', { name: /Start trial/ })
    .first()
    .click();

  await expect(page).toHaveURL(/\/marketplace\/digital-marketing\?.*intent=trial/);
  expect(await shellElement?.evaluate((element) => element.isConnected)).toBe(true);
  await expect(page.getByRole('link', { name: 'WAOOAW home' })).toBeVisible();
  await expect(page.getByText('You chose to start a trial.')).toBeVisible();
  await expect(page.getByText('No paid tools')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms');
  await expect(page.getByRole('link', { name: 'Privacy Policy' })).toHaveAttribute('href', '/privacy');
  await expect(page.getByText('Terms version 2026-07-18.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Continue to trial' })).toBeDisabled();
  expect(documents).toHaveLength(1);
  await expectIntegrity(page);
  await page.screenshot({ path: testInfo.outputPath('marketplace-trial-review.png'), fullPage: true });
});

test('WC097-A04-A07: Hire review preserves intent and the customer shell', async ({ page }, testInfo) => {
  const documents: string[] = [];
  page.on('request', (request) => {
    if (request.resourceType() === 'document') documents.push(request.url());
  });
  await page.goto('/marketplace');
  await expectShellReady(page);
  const shellElement = await page.locator('.app-shell-customer:visible').elementHandle();

  await page.getByRole('link', { name: /Hire/ }).first().click();

  await expect(page).toHaveURL(/\/marketplace\/digital-marketing\?.*intent=hire/);
  expect(await shellElement?.evaluate((element) => element.isConnected)).toBe(true);
  await expect(page.getByText('You chose to hire this professional.')).toBeVisible();
  await expect(page.getByText('Professional plan')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Continue to hire' })).toBeDisabled();
  expect(documents).toHaveLength(1);
  await expectIntegrity(page);
  await page.screenshot({ path: testInfo.outputPath('marketplace-hire-review.png'), fullPage: true });
});
