// Implements: work-contracts/WC-107-fundamental-customer-journey-integrity.md R009, R010, R012, R017
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
    await expect(page.getByRole('button', { name: 'Ask about professionals' })).toBeVisible();
  }
}

async function expectShellReady(page: Page) {
  if ((page.viewportSize()?.width ?? 0) <= 599) return;
  await page.getByRole('button', { name: 'Expand navigation' }).click();
  await expect(page.getByRole('button', { name: 'Collapse navigation' })).toBeVisible();
  await page.getByRole('button', { name: 'Collapse navigation' }).click();
  await expect(page.getByRole('button', { name: 'Expand navigation' })).toBeVisible();
}

test.beforeEach(async ({ context }, testInfo) => {
  await context.clearCookies();
  await addSession(context, testInfo.project.name);
});

test('WC107-MARKETPLACE-01: complete card exposes a consent-gated Trial and Hire decision', async ({
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
  const card = page.locator('.marketplace-offer').first();
  await expect(card.getByRole('list', { name: 'Included capabilities' }).getByRole('listitem')).toHaveCount(3);
  await card.getByText('Scope, safeguards and your control').click();
  await expect(card.getByText('No guaranteed outcome')).toBeVisible();
  await expect(card.getByText('Stop at any time')).toBeVisible();
  const consent = card.getByRole('checkbox');
  const trial = card.getByRole('button', { name: 'Start 14-day trial' });
  const hire = card.getByRole('button', { name: 'Hire for ₹2,499.00' });
  await expect(trial).toBeDisabled();
  await expect(hire).toBeDisabled();
  await consent.check();
  await expect(trial).toBeEnabled();
  await expect(hire).toBeEnabled();
  await consent.uncheck();
  await expect(trial).toBeDisabled();
  await expect(hire).toBeDisabled();
  expect(new URL(page.url()).search).toBe('');
  await page.screenshot({ path: testInfo.outputPath('marketplace-card.png'), fullPage: true });
  expect(await shellElement?.evaluate((element) => element.isConnected)).toBe(true);
  await expect(card.getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms');
  await expect(card.getByRole('link', { name: 'Privacy Policy' })).toHaveAttribute('href', '/privacy');
  expect(documents).toHaveLength(1);
  await expectIntegrity(page);
});

test('WC107-MARKETPLACE-02: cancelling leaves acquisition state and browser history unchanged', async ({ page }) => {
  await page.goto('/marketplace');
  const cleanUrl = page.url();
  const historyLength = await page.evaluate(() => history.length);
  await page.locator('.marketplace-offer').first().getByRole('link', { name: 'Not now' }).click();
  await expect(page).toHaveURL(cleanUrl);
  expect(await page.evaluate(() => history.length)).toBe(historyLength);
  await expect(
    page.locator('.marketplace-offer').first().getByRole('button', { name: 'Start 14-day trial' })
  ).toBeDisabled();
});

test('WC107-MARKETPLACE-03: validated coupon updates Hire without entering URL or history', async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'One desktop journey proves private pre-checkout state.');
  await page.route('**/api/acquisition/hire-preview', async (route) => {
    expect(JSON.parse(route.request().postData() ?? '{}')).toEqual({
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      professionalVersion: '1.0.0',
      couponCode: 'DEMO100',
    });
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ coupon_code: 'DEMO100', payable_inr_paise: 0 }),
    });
  });
  await page.goto('/marketplace');
  const cleanUrl = page.url();
  const historyLength = await page.evaluate(() => history.length);
  const card = page.locator('.marketplace-offer').first();

  await card.getByLabel('Coupon code (optional)').fill('demo100');
  await card.getByRole('button', { name: 'Apply' }).click();
  await expect(card.getByRole('button', { name: 'Hire for ₹0.00' })).toBeDisabled();
  expect(page.url()).toBe(cleanUrl);
  expect(await page.evaluate(() => history.length)).toBe(historyLength);

  await card.getByLabel('Coupon code (optional)').fill('changed');
  await expect(card.getByRole('button', { name: 'Hire for ₹2,499.00' })).toBeDisabled();
  await expect(card.getByText('Coupon applied. Amount due now: ₹0.00.')).toHaveCount(0);
});
