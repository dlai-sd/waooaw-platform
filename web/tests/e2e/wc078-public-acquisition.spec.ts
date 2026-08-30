import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { messages } from '../../lib/i18n';
import { supportedLocales, type SupportedLocale } from '../../lib/preferences';

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
  const acquisitionEvents: string[] = [];
  page.on('request', (request) => { if (/google-analytics|googletagmanager|facebook|connect\.facebook/.test(request.url())) marketingRequests.push(request.url()); });
  page.on('request', (request) => { if (request.url().endsWith('/api/acquisition/events')) acquisitionEvents.push(String(request.postDataJSON().event_name)); });
  await page.goto('/contact');
  expect(acquisitionEvents).toEqual([]);
  for (const link of await page.locator('a[href^="mailto:"]').all()) await expect(link).toHaveAttribute('href', 'mailto:customersupport@dlaisd.com');
  await page.getByRole('button', { name: 'Reject optional' }).click();
  expect(decodeURIComponent((await page.context().cookies()).find((cookie) => cookie.name === 'waooaw_consent')?.value ?? '')).toContain('"analytics":false');
  await page.getByRole('button', { name: 'Cookie preferences' }).click();
  await page.getByRole('checkbox', { name: 'Analytics' }).check();
  await page.waitForFunction(() => document.readyState === 'complete');
  await page.getByRole('button', { name: 'Save preferences' }).click();
  expect(decodeURIComponent((await page.context().cookies()).find((cookie) => cookie.name === 'waooaw_consent')?.value ?? '')).toContain('"analytics":true');
  await expect.poll(() => acquisitionEvents).toEqual(['consent_updated', 'consent_updated', 'public_page_viewed']);
  expect(marketingRequests).toEqual([]);
});

test('PA-ACC-16: keyboard and axe checks pass across the public acquisition surface', async ({ page }) => {
  for (const path of ['/', '/professionals', '/contact', '/privacy']) {
    await page.goto(path);
    const skipLink = page.getByRole('link', { name: 'Skip to main content' });
    await skipLink.focus();
    await expect(skipLink).toBeFocused();
    await skipLink.press('Enter');
    await expect(page.locator('#main-content')).toBeFocused();
    await page.locator('body').evaluate(async () => { await Promise.all(document.getAnimations().map((animation) => animation.finished)); });
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations.filter((finding) => finding.impact === 'critical' || finding.impact === 'serious'), path).toEqual([]);
  }
});

test('PA-ACC-05 PA-ACC-14: locale, theme, security headers, and PWA policy are complete', async ({ context, page, request }) => {
  await page.setViewportSize({ width: 720, height: 900 });
  const expectedFamily: Record<SupportedLocale, RegExp> = {
    en: /Noto[ _]Sans/i, hi: /Devanagari/i, mr: /Devanagari/i, ta: /Tamil/i, te: /Telugu/i,
    kn: /Kannada/i, gu: /Gujarati/i, bn: /Bengali/i, ml: /Malayalam/i, pa: /Gurmukhi/i, ur: /Nastaliq/i,
  };
  for (const locale of supportedLocales) {
    await context.addCookies([{ name: 'waooaw-locale', value: locale, url: baseURL }]);
    await page.goto('/');
    await expect(page.locator('html')).toHaveAttribute('lang', locale);
    await expect(page.locator('html')).toHaveAttribute('dir', locale === 'ur' ? 'rtl' : 'ltr');
    await expect(page.getByRole('link', { name: new RegExp(messages[locale].browseProfessionals) }).first()).toBeVisible();
    expect(await page.locator('body').evaluate((element) => getComputedStyle(element).fontFamily)).toMatch(expectedFamily[locale]);
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), `${locale} must reflow at 200%`).toBe(false);
  }
  const response = await request.get('/');
  const csp = response.headers()['content-security-policy'];
  expect(csp).toContain("script-src 'self' 'nonce-");
  expect(csp).not.toContain("script-src 'self' 'unsafe-inline'");
  expect(csp).not.toContain('unsafe-eval');
  expect(csp).not.toContain('*');
  expect(response.headers()['strict-transport-security']).toContain('max-age=31536000');
  await page.goto('/');
  expect(await page.locator('script[nonce]').count()).toBeGreaterThan(0);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
  expect(await (await request.get('/manifest.webmanifest')).json()).toMatchObject({ display: 'standalone', name: 'WAOOAW', scope: '/', short_name: 'WAOOAW' });
  const worker = await (await request.get('/sw.js')).text();
  expect(worker).toContain('waooaw-static-shell-v1');
  expect(worker).toContain('NetworkOnly');
  expect(worker).not.toMatch(/(?:apis|pages|rsc|cross-origin)-|waooaw_consent|app\/api\/|app\/\((?:auth|authenticated|founder)\)\//i);
});

test('PA-ACC-02 PA-ACC-08: legal source and sole-contact projection render in production', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Built through a connected institutional lineage.' })).toBeVisible();
  await expect(page.locator('.platform-dna')).toContainText('Yashus');
  await expect(page.locator('.platform-dna')).toContainText('DLAI Satellite Data');
  await page.goto('/privacy');
  await expect(page.getByRole('heading', { name: 'The Three-Ledger Model — Your Constitutional Ownership' })).toBeVisible();
  await expect(page.getByText('Effective Date:')).toBeVisible();
  await page.goto('/cookies');
  await expect(page.getByRole('heading', { name: 'Runtime preference record' })).toBeVisible();
  await page.goto('/grievance');
  await expect(page.getByRole('heading', { name: 'Constitutional Grievance — Special Process' })).toBeVisible();
  const body = await page.locator('body').innerText();
  expect(body).toContain('customersupport@dlaisd.com');
  expect(body).not.toMatch(/technology@dlaisd\.com|yogesh\.khandge@dlaisd\.com|8888912344/);
});

test('PA-ACC-15: expanded Chromium public payload and vitals stay within budget', async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== 'chromium-expanded', 'Performance uses the approved expanded Chromium profile.');
  await page.addInitScript(() => {
    const vitals = { cls: 0, lcp: 0, lcpObserved: false };
    Object.defineProperty(window, '__wc078Vitals', { value: vitals });
    new PerformanceObserver((list) => { for (const entry of list.getEntries()) { vitals.lcp = entry.startTime; vitals.lcpObserved = true; } }).observe({ type: 'largest-contentful-paint', buffered: true });
    new PerformanceObserver((list) => { for (const entry of list.getEntries() as Array<PerformanceEntry & { hadRecentInput: boolean; value: number }>) if (!entry.hadRecentInput) vitals.cls += entry.value; }).observe({ type: 'layout-shift', buffered: true });
  });
  const initialHtml = await (await request.get('/')).text();
  await page.goto('/');
  await page.getByRole('button', { name: messages.en.darkTheme }).click();
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  const metrics = await page.evaluate((html) => {
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    const documentHtml = new DOMParser().parseFromString(html, 'text/html');
    const scripts = new Set([...documentHtml.scripts].map((script) => script.getAttribute('src')).filter((source): source is string => Boolean(source)).map((source) => new URL(source, location.origin).href));
    const initial = new Set([...scripts, ...[...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"]')].map((link) => link.href), ...[...document.images].map((image) => image.currentSrc || image.src)]);
    const selected = resources.filter((entry) => initial.has(entry.name) || entry.initiatorType === 'font');
    const vitals = (window as typeof window & { __wc078Vitals: { cls: number; lcp: number; lcpObserved: boolean } }).__wc078Vitals;
    return {
      ...vitals,
      fcp: performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? 0,
      initialJsBytes: resources.filter((entry) => scripts.has(entry.name)).reduce((total, entry) => total + entry.encodedBodySize, 0),
      scripts: resources.filter((entry) => scripts.has(entry.name)).map((entry) => ({ name: entry.name, bytes: entry.encodedBodySize })),
      publicBytes: ((performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming)?.encodedBodySize ?? 0) + selected.reduce((total, entry) => total + entry.encodedBodySize, 0),
    };
  }, initialHtml);
  expect(metrics.fcp).toBeLessThanOrEqual(1500);
  expect(metrics.lcpObserved).toBe(true);
  expect(metrics.lcp).toBeLessThanOrEqual(2500);
  expect(metrics.cls).toBeLessThanOrEqual(0.1);
  expect(metrics.initialJsBytes, JSON.stringify(metrics.scripts)).toBeLessThanOrEqual(125 * 1024);
  expect(metrics.publicBytes).toBeLessThanOrEqual(200 * 1024);
  await page.screenshot({ path: testInfo.outputPath('public-home-reviewed.png'), fullPage: true, animations: 'disabled' });
});