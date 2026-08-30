import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const publicRoutes = ['/', '/professionals', '/blogs', '/about', '/contact', '/careers', '/press', '/constitution', '/privacy', '/terms', '/cookies', '/refund', '/grievance'];
const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:3000';

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
  await context.addCookies([{ name: 'waooaw-locale', value: 'en', url: baseURL }]);
});

test('PA-ACC-03 PA-ACC-05: handoff is stable, reduced-motion, responsive, and RTL-safe', async ({ context, page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'From trial to autonomous productivity — in minutes' })).toBeVisible();
  await expect(page.locator('.handoff-console li')).toHaveCount(4);
  expect(await page.locator('.handoff-console li').first().evaluate((row) => ({ opacity: getComputedStyle(row).opacity, transform: getComputedStyle(row).transform }))).toEqual({ opacity: '1', transform: 'none' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  await context.addCookies([{ name: 'waooaw-locale', value: 'ur', url: baseURL }]);
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});

test('PA-ACC-06 PA-ACC-07: public routes expose crawlable metadata and typed structured data', async ({ page, request }) => {
  for (const path of publicRoutes) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(200);
    await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', path === '/' ? /^https:\/\/waooaw\.com\/?$/ : new RegExp(`${path}$`));
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute('content', /.+/);
  }
  await page.goto('/professionals/digital-marketing');
  expect(JSON.parse(await page.locator('script[type="application/ld+json"]').textContent() ?? '[]').map((item: { '@type': string }) => item['@type'])).toEqual(['Service', 'BreadcrumbList']);
  await page.goto('/blogs/governed-digital-professional');
  expect(JSON.parse(await page.locator('script[type="application/ld+json"]').textContent() ?? '[]')[0]['@type']).toBe('Article');
  expect((await request.get('/professionals/not-published')).status()).toBe(404);
  expect((await request.get('/blogs/not-published')).status()).toBe(404);
  expect(await (await request.get('/robots.txt')).text()).toContain('Disallow: /');
  expect(await (await request.get('/sitemap.xml')).text()).not.toContain('/login');
});

test('PA-ACC-08 PA-ACC-10 PA-ACC-13: contact and optional acquisition remain privacy-governed', async ({ page }) => {
  const marketingRequests: string[] = [];
  page.on('request', (request) => { if (/google-analytics|googletagmanager|facebook|connect\.facebook/.test(request.url())) marketingRequests.push(request.url()); });
  await page.goto('/contact');
  for (const link of await page.locator('a[href^="mailto:"]').all()) await expect(link).toHaveAttribute('href', 'mailto:customersupport@dlaisd.com');
  await page.getByRole('button', { name: 'Reject optional' }).click();
  expect(decodeURIComponent((await page.context().cookies()).find((cookie) => cookie.name === 'waooaw_consent')?.value ?? '')).toContain('"analytics":false');
  await page.getByRole('button', { name: 'Cookie preferences' }).click();
  await page.getByRole('checkbox', { name: 'Analytics' }).check();
  await page.getByRole('button', { name: 'Save preferences' }).click();
  expect(decodeURIComponent((await page.context().cookies()).find((cookie) => cookie.name === 'waooaw_consent')?.value ?? '')).toContain('"analytics":true');
  expect(marketingRequests).toEqual([]);
});

test('PA-ACC-16: keyboard and axe checks pass across the public acquisition surface', async ({ page }) => {
  for (const path of ['/', '/professionals', '/contact', '/privacy']) {
    await page.goto(path);
    await page.keyboard.press('Tab');
    await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused();
    await page.locator('body').evaluate(async () => { await Promise.all(document.getAnimations().map((animation) => animation.finished)); });
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations.filter((finding) => finding.impact === 'critical' || finding.impact === 'serious'), path).toEqual([]);
  }
});