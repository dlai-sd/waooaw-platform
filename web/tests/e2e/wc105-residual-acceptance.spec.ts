// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R022, WC105-R023
// Constitutional basis: C-001, C-005, C-023, C-026, C-049, C-059, C-063

import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';

async function addSession(context: BrowserContext, actor: string) {
  const value = await encode({
    secret,
    maxAge: 3600,
    token: {
      accessToken: `fixture-access-token-wc105-${actor}`,
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 3600,
      founder: false,
      sub: `fixture-user-wc105-${actor}`,
    },
  });
  await context.addCookies([
    { name: 'next-auth.session-token', value, domain: '127.0.0.1', httpOnly: true, path: '/', sameSite: 'Lax' },
  ]);
}

async function acquire(page: Page, intent: 'trial' | 'hire', idempotencyKey: string) {
  return page.evaluate(
    async ({ selectedIntent, key }) => {
      const response = await fetch('/api/acquisition/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
          professionalVersion: '1.0.0',
          intent: selectedIntent,
          disclosureRevision: '1.0.0',
          termsVersion: '2026-07-18',
          idempotencyKey: key,
        }),
      });
      return { status: response.status, body: await response.json() };
    },
    { selectedIntent: intent, key: idempotencyKey }
  );
}

test('WC105-R022 R023: acquired DMA relationships persist, isolate, verify a goal, and start governed work', async ({
  context,
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'One expanded Chromium journey proves the lifecycle.');
  await context.clearCookies();
  await addSession(context, 'owner');
  await page.goto('/marketplace');

  const trialKey = '11111111-1111-4111-8111-111111111111';
  const hireKey = '22222222-2222-4222-8222-222222222222';
  const trial = await acquire(page, 'trial', trialKey);
  const replay = await acquire(page, 'trial', trialKey);
  const hire = await acquire(page, 'hire', hireKey);
  expect(trial.status).toBe(200);
  expect(replay.body.relationshipId).toBe(trial.body.relationshipId);
  expect(hire.status).toBe(200);

  await page.goto('/professionals/mine');
  const trialCard = page.getByRole('heading', { name: 'Digital Marketing Trial' }).locator('xpath=ancestor::li[1]');
  const hireCard = page.getByRole('heading', { name: 'Digital Marketing Hire' }).locator('xpath=ancestor::li[1]');
  await expect(trialCard).toHaveCount(1);
  await expect(hireCard).toHaveCount(1);
  await expect(trialCard.getByText('ACTIVE', { exact: true })).toBeVisible();
  await expect(hireCard.getByText('CONTRACT PENDING ACCEPTANCE', { exact: true })).toBeVisible();

  await context.clearCookies();
  await addSession(context, 'owner');
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Digital Marketing Trial' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Digital Marketing Hire' })).toBeVisible();

  await context.clearCookies();
  await addSession(context, 'other-tenant');
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Digital Marketing Trial' })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Digital Marketing Hire' })).toHaveCount(0);

  await context.clearCookies();
  await addSession(context, 'owner');
  await page.goto(`/relationships/${trial.body.relationshipId}`);
  await page.getByRole('button', { name: 'Verify goal' }).click();
  await expect(page.getByText('Goal verification recorded.')).toBeVisible();
  await page.reload();
  await expect(page.getByText('1 of 1 verified').first()).toBeVisible();
  await expect(page.getByText('eligible', { exact: true }).first()).toBeVisible();

  await page.getByRole('button', { name: 'Open conversation' }).first().click();
  const conversation = page.getByRole('complementary', { name: 'Professional conversation' });
  await expect(conversation.getByLabel('Conversation timeline')).toHaveAttribute('aria-busy', 'false');
  await conversation.getByLabel('Message your professional').fill('Prepare the approved campaign plan.');
  await expect(conversation.getByRole('button', { name: 'Send' })).toBeEnabled();
  await conversation.getByRole('button', { name: 'Send' }).click();
  await expect(
    conversation.getByLabel('Conversation timeline').getByText('Prepare the approved campaign plan.')
  ).toBeVisible();
  await expect(conversation.getByText('Accepted by WAOOAW')).toBeVisible();
  await expect(conversation.getByText('Professional processing', { exact: true })).toBeVisible();
  await expect(conversation.getByText('Evidence pending', { exact: true })).toBeVisible();
});

test('WC105-R024 R025 R026: feature rail, trust copy, and enlarged logo remain usable across presentation modes', async ({
  context,
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== 'chromium-expanded',
    'One Chromium instance controls the complete viewport matrix.'
  );
  await context.clearCookies();
  const viewports = [
    { width: 1440, height: 900, logoWidth: 108, logoHeight: 108 },
    { width: 390, height: 844, logoWidth: 66, logoHeight: 66 },
  ];
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto('/');
    await expect(page.getByText('Control remains yours.', { exact: true })).toBeVisible();
    await expect(page.getByText('Trust grows when you can see the work')).toBeVisible();
    await expect(page.getByText('How your professional works with you')).toBeVisible();
    await expect(page.getByText('Clear rules. Your business stays in control.')).toBeVisible();
    await expect(page.getByText('Work with your WAOOAW professional on WhatsApp')).toBeVisible();
    const logo = page.getByRole('link', { name: 'WAOOAW home' }).locator('img');
    const logoBox = await logo.boundingBox();
    expect(logoBox?.width).toBeCloseTo(viewport.logoWidth, 0);
    expect(logoBox?.height).toBeCloseTo(viewport.logoHeight, 0);
    await page.getByRole('button', { name: 'Next platform feature' }).click();
    await expect(page.getByText('Built for real business growth')).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)
    ).toBe(true);
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.evaluate(() => {
    document.documentElement.style.fontSize = '200%';
  });
  await expect(page.getByText('Trust grows when you can see the work')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Next platform feature' })).toBeVisible();
  const zoomedLogoBox = await page.getByRole('link', { name: 'WAOOAW home' }).locator('img').boundingBox();
  expect(zoomedLogoBox?.width).toBeCloseTo(66, 0);
  expect(zoomedLogoBox?.height).toBeCloseTo(66, 0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(
    true
  );

  await context.addCookies([{ name: 'waooaw-locale', value: 'ur', domain: '127.0.0.1', path: '/' }]);
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByRole('region', { name: 'Platform features' })).toBeVisible();
  await expect(page.getByText('کام نظر آئے تو اعتماد بڑھتا ہے')).toBeVisible();
  await expect(page.getByText('واضح اصول۔ آپ کے کاروبار کا اختیار آپ کے پاس رہتا ہے۔')).toBeVisible();
  await expect(page.getByText('ثبوت سے اعتماد بڑھتا ہے')).toHaveCount(0);
  await expect(page.getByText('تحریری آئین کے تحت')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(
    true
  );
});
