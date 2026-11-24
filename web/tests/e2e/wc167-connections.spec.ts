// Implements: work-contracts/WC-167-acceptance-demo-readiness.md WC167-R002, WC167-R006
// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-RESP-01, §UX-SHELL-03, §UX-VIS
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import AxeBuilder from '@axe-core/playwright';
import { type BrowserContext, type Page, expect, test } from '@playwright/test';
import { encode } from 'next-auth/jwt';

const secret = 'playwright-only-not-a-runtime-secret';
const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:3000';
const host = new URL(baseURL).hostname;

async function signIn(context: BrowserContext, theme: 'light' | 'dark') {
  const value = await encode({
    secret,
    maxAge: 60 * 60,
    token: {
      accessToken: 'fixture-access-token',
      accessTokenExpiresAt: Math.floor(Date.now() / 1000) + 3600,
      founder: false,
      sub: 'fixture-user',
    },
  });
  await context.clearCookies();
  await context.addCookies([
    { name: 'next-auth.session-token', value, domain: host, httpOnly: true, path: '/', sameSite: 'Lax' },
    { name: 'waooaw-locale', value: 'en', domain: host, path: '/' },
    { name: 'waooaw-theme', value: theme, domain: host, path: '/' },
  ]);
}

function answerConnections(page: Page, status: number, body: unknown) {
  return page.route('**/api/provider-connections', (route) =>
    route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
  );
}

async function expectClean(page: Page, label: string) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(overflow, `${label} must not scroll sideways`).toBe(false);
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter(
    (violation) => violation.impact === 'critical' || violation.impact === 'serious'
  );
  expect(blocking, `${label} has serious or critical axe findings`).toEqual([]);
}

const states = [
  {
    name: 'expired sign-in',
    status: 401,
    body: { code: 'CONNECTION_SIGN_IN_REQUIRED' },
    text: /Your sign-in has expired/,
    link: { name: 'Sign in again', href: '/login?returnTo=%2Fconnections' },
  },
  {
    name: 'no customer account',
    status: 403,
    body: { code: 'CONNECTION_ACCOUNT_REQUIRED' },
    text: /Start a trial or hire an agent first/,
    link: { name: 'Browse the marketplace', href: '/marketplace' },
  },
  {
    name: 'real permission refusal',
    status: 403,
    body: { code: 'CONNECTION_FORBIDDEN' },
    text: /not permitted to manage this connection/,
    link: null,
  },
  {
    name: 'unavailable',
    status: 503,
    body: { code: 'CONNECTION_UNAVAILABLE' },
    text: /temporarily unavailable/,
    link: null,
  },
] as const;

for (const theme of ['light', 'dark'] as const) {
  for (const state of states) {
    test(`WC167-R002 WC167-R006: Connections ${state.name} is honest, reflows and passes axe (${theme})`, async ({
      context,
      page,
    }, testInfo) => {
      await signIn(context, theme);
      await answerConnections(page, state.status, state.body);
      await page.goto('/connections');

      const alert = page.getByRole('main').getByRole('alert');
      await expect(alert).toContainText(state.text);
      if (state.name !== 'real permission refusal') await expect(alert).not.toContainText(/not permitted/);
      if (state.link) {
        await expect(page.getByRole('link', { name: state.link.name })).toHaveAttribute('href', state.link.href);
      }
      await expect(page.getByRole('button', { name: 'Try again' })).toBeEnabled();
      await expectClean(page, `${state.name} at ${testInfo.project.name} in ${theme}`);
      await page.screenshot({ path: testInfo.outputPath(`connections-${state.name.replace(/ /g, '-')}-${theme}.png`) });
    });
  }

  test(`WC167-R006: Connections ready and empty states reflow and pass axe (${theme})`, async ({
    context,
    page,
  }, testInfo) => {
    await signIn(context, theme);
    await answerConnections(page, 200, []);
    await page.goto('/connections');

    await expect(page.getByRole('button', { name: /Connect Facebook/ })).toBeEnabled();
    await expect(page.getByText(/You have not connected any accounts yet/)).toBeVisible();
    await expectClean(page, `empty at ${testInfo.project.name} in ${theme}`);
    await page.screenshot({ path: testInfo.outputPath(`connections-empty-${theme}.png`) });
  });
}

test('WC167-R001 WC167-R006: a signed-in customer sees no Founder or administrative navigation', async ({
  context,
  page,
}) => {
  await signIn(context, 'light');
  await answerConnections(page, 200, []);
  await page.goto('/connections');

  await expect(page.getByRole('heading', { name: 'Connections' })).toBeVisible();
  for (const label of ['Providers', 'Pricing', 'Azure Key Vault']) {
    await expect(page.getByRole('link', { name: label })).toHaveCount(0);
  }
});
