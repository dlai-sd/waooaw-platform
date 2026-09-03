// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Acceptance Matrix
// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §19 (VRA-01 through VRA-20), §11.1 (WC-07/WC-08 manifest)
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability)

import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { messages } from '../../lib/i18n';
import { supportedLocales, type SupportedLocale } from '../../lib/preferences';
import { wc078CollisionCaseId, wc078ScreenshotManifest } from './wc078-screenshot-manifest';

const publicRoutes = ['/', '/professionals', '/blogs', '/about', '/contact', '/careers', '/press', '/constitution', '/privacy', '/terms', '/cookies', '/refund', '/grievance'];
const baseURL = process.env.BASE_URL ?? 'http://127.0.0.1:3000';

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
  await context.addCookies([{ name: 'waooaw-locale', value: 'en', url: baseURL }]);
});

test('VRA-02 VRA-03 VRA-05 (PA-ACC-03 superseded per plan §2 — old hero-console heading/`.handoff-console` replaced by the journey showcase): hero heading, journey showcase, four rails, reduced-motion settle, 360px overflow, and Urdu RTL', async ({ context, page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Grow your business with WAOOAW AI professionals' })).toBeVisible();
  await expect(page.locator('.journey-showcase')).toBeVisible();
  const journeyRail = page.getByRole('navigation', { name: 'Journey stages' });
  for (const label of ['Business', 'Goals', 'Ways of working', 'Working 24/7']) {
    await expect(journeyRail.getByRole('button', { name: label, exact: true })).toBeVisible();
  }
  await expect(page.locator('.journey-settled')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
  await context.addCookies([{ name: 'waooaw-locale', value: 'ur', url: baseURL }]);
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});

test('VRA-04: both professional stories expose all six semantic stages through the four rail controls', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Reject optional' }).click();
  await expect(page.getByRole('button', { name: /Agricultural Advisor/ })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: /Digital Marketing Professional/ }).click();
  await expect(page.getByRole('button', { name: /Digital Marketing Professional/ })).toHaveAttribute('aria-pressed', 'true');
  const journeyRail = page.getByRole('navigation', { name: 'Journey stages' });
  for (const label of ['Business', 'Goals', 'Ways of working', 'Working 24/7']) {
    const railButton = journeyRail.getByRole('button', { name: label, exact: true });
    await railButton.click();
    await expect(railButton).toHaveAttribute('aria-pressed', 'true');
  }
});

test('VRA-09: hero and final CTAs share one truthful primary/secondary command hierarchy', async ({ page }) => {
  await page.goto('/');
  const primaries = page.locator('a.primary-link[href="/professionals"]');
  const secondaries = page.locator('a.secondary-link[href="/register"]');
  await expect(primaries).toHaveCount(2);
  await expect(secondaries).toHaveCount(2);
  for (const link of await primaries.all()) expect(await link.evaluate((element) => getComputedStyle(element).backgroundColor)).not.toBe('rgba(0, 0, 0, 0)');
  for (const link of await secondaries.all()) expect(await link.evaluate((element) => getComputedStyle(element).borderStyle)).toBe('solid');
});

test('VRA-07: Platform DNA names Yashus, DLAI Satellite Data, and WAOOAW with visible roles', async ({ page }) => {
  await page.goto('/');
  const dna = page.locator('.platform-dna');
  await expect(dna).toBeVisible();
  for (const name of ['Yashus', 'DLAI Satellite Data', 'WAOOAW']) await expect(dna).toContainText(name);
});

test('VR-05 regression, VRA-02: cookie preferences remain reachable from the footer and no duplicate getting-started heading renders', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Getting started', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Reject optional' }).click();
  await expect(page.getByRole('complementary', { name: 'Cookie preferences' })).toBeHidden();
  await page.getByRole('button', { name: 'Cookie preferences' }).click();
  await expect(page.getByRole('complementary', { name: 'Cookie preferences' })).toBeVisible();
});

test('VRA-10: fixed-control collision assertion catches a seeded overlap at 360px with announcement and consent surfaces active', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto('/');
  function overlaps(a: { top: number; right: number; bottom: number; left: number }, b: typeof a): boolean {
    return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
  }
  const readFixtureRects = () => page.evaluate(() => ['wc078-fixture-a', 'wc078-fixture-b'].map((id) => {
    const rect = document.getElementById(id)!.getBoundingClientRect();
    return { top: rect.top, right: rect.right, bottom: rect.bottom, left: rect.left };
  }));
  await page.evaluate(() => {
    const announcement = document.createElement('div');
    announcement.id = 'wc078-fixture-a';
    announcement.style.cssText = 'position:fixed;inset-block-start:0;inset-inline-start:0;width:200px;height:48px;z-index:45;';
    document.body.appendChild(announcement);
    const consent = document.createElement('div');
    consent.id = 'wc078-fixture-b';
    consent.style.cssText = 'position:fixed;inset-block-start:0;inset-inline-start:0;width:200px;height:48px;z-index:70;';
    document.body.appendChild(consent);
  });
  const [seededA, seededB] = await readFixtureRects();
  expect(overlaps(seededA, seededB)).toBe(true);
  await page.evaluate(() => { document.getElementById('wc078-fixture-b')!.style.insetBlockStart = '400px'; });
  const [separatedA, separatedB] = await readFixtureRects();
  expect(overlaps(separatedA, separatedB)).toBe(false);
});

test('VRA-14: Section 11.1 screenshot manifest declares exactly 54 deterministic cases with a resolvable G9 reference (declaration only; WC-08 executes captures)', () => {
  const ids = new Set(wc078ScreenshotManifest.map((entry) => entry.id));
  expect(wc078ScreenshotManifest.length).toBe(54);
  expect(ids.size).toBe(54);
  expect(wc078ScreenshotManifest.some((entry) => entry.id === wc078CollisionCaseId)).toBe(true);
});

test('VRA-14 axis coverage: every required Section 11.1 dimension value appears at least once in the manifest (declaration only; WC-08 executes captures, WC-09 binds VRA-15 substantive review)', () => {
  const values = <T,>(selector: (entry: (typeof wc078ScreenshotManifest)[number]) => T | undefined) =>
    new Set(wc078ScreenshotManifest.map(selector).filter((value): value is T => value !== undefined));

  expect(values((entry) => `${entry.viewport.width}x${entry.viewport.height}`)).toEqual(new Set(['360x800', '768x1024', '1440x900']));
  expect(values((entry) => entry.zoom)).toEqual(new Set(['default', '200%']));
  expect(values((entry) => entry.theme)).toEqual(new Set(['light', 'dark', 'system']));
  expect(values((entry) => entry.motion)).toEqual(new Set(['normal', 'reduced']));
  expect(values((entry) => entry.announcement)).toEqual(new Set(['visible', 'dismissed']));
  expect(values((entry) => entry.consent)).toEqual(new Set(['banner', 'preferences-open', 'closed']));

  const locales = values((entry) => entry.locale);
  expect(locales.has('en')).toBe(true);
  expect(locales.has('ur')).toBe(true); // RTL sample
  expect(locales.has('hi')).toBe(true); // Devanagari sample
  expect(locales.has('ta')).toBe(true); // Dravidian sample

  const professionals = values((entry) => entry.professional);
  const stages = values((entry) => entry.stage);
  expect(professionals).toEqual(new Set(['agricultural-advisor', 'digital-marketing-professional']));
  expect(stages).toEqual(new Set(['opening', 'business', 'goals', 'agreement', 'ready', 'working']));

  for (const professional of professionals) {
    for (const compactViewport of [{ width: 360, height: 800 }, { width: 1440, height: 900 }]) {
      const stagesForProfessional = new Set(
        wc078ScreenshotManifest
          .filter((entry) => entry.professional === professional && entry.viewport.width === compactViewport.width && entry.viewport.height === compactViewport.height)
          .map((entry) => entry.stage),
      );
      expect(stagesForProfessional, `${professional} at ${compactViewport.width}x${compactViewport.height} must cover all six semantic stages`).toEqual(stages);
    }
  }
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