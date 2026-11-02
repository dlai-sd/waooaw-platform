import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { createServer } from 'node:https';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium, firefox, webkit } from '@playwright/test';
import { getToken } from 'next-auth/jwt';

let input = '';
for await (const chunk of process.stdin) input += chunk;
const { browserName, scenarios, secret } = JSON.parse(input);
const directory = mkdtempSync(join(tmpdir(), 'logout-cookie-browser-'));
const key = join(directory, 'key.pem');
const cert = join(directory, 'cert.pem');
execFileSync(
  'openssl',
  [
    'req',
    '-x509',
    '-newkey',
    'rsa:2048',
    '-nodes',
    '-keyout',
    key,
    '-out',
    cert,
    '-days',
    '1',
    '-subj',
    '/CN=localhost',
  ],
  { stdio: 'ignore' }
);
let step;
const server = createServer({ key: readFileSync(key), cert: readFileSync(cert) }, (request, response) => {
  if (request.url === '/browser-harness') {
    response.writeHead(200, { 'content-type': 'text/html' });
    response.end('<!doctype html><title>Logout cookie test</title>');
    return;
  }
  assert.equal(request.url, new URL(step.url).pathname + new URL(step.url).search);
  assert.equal(request.method, step.method);
  response.writeHead(
    step.status,
    step.headers.flatMap(({ name, value }) => [name, value])
  );
  response.end(step.body);
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `https://127.0.0.1:${server.address().port}`;
let browser;

try {
  browser = await { chromium, firefox, webkit }[browserName].launch();
  for (const scenario of scenarios) {
    const context = await browser.newContext({ ignoreHTTPSErrors: true });
    try {
      await context.addCookies(scenario.cookies.map(({ domain, ...cookie }) => ({ ...cookie, domain: '127.0.0.1' })));
      const initialCookies = await context.cookies();
      for (const cookie of scenario.cookies) {
        assert.equal(initialCookies.find(({ name }) => name === cookie.name)?.value, cookie.value);
      }
      if (scenario.authenticatedJwt) {
        const token = await getToken({
          req: {
            cookies: Object.fromEntries(initialCookies.map(({ name, value }) => [name, value])),
            headers: {},
          },
          secret,
          secureCookie: true,
        });
        assert.equal(typeof token?.accessToken, 'string', `${scenario.name}: initial JWT must authenticate`);
      }
      const page = await context.newPage();
      await context.route('**/*', async (route) => {
        assert.equal(new URL(route.request().url()).origin, origin, 'Browser test must not access a real provider');
        await route.continue();
      });
      await page.goto(`${origin}/browser-harness`);
      for (step of scenario.steps) {
        const status = await page.evaluate(
          async ({ url, method }) => {
            return (await fetch(url, { method, redirect: 'manual' })).status;
          },
          { url: step.url.replace('https://app.example', origin), method: step.method }
        );
        assert.equal(status, step.status === 303 ? 0 : step.status);
        const cookies = await context.cookies();
        const remaining = new Set(cookies.map(({ name }) => name));
        for (const name of step.absent) {
          assert.equal(remaining.has(name), false, `${scenario.name}: ${name} survived ${step.method}`);
        }
        for (const name of step.present) {
          assert.equal(remaining.has(name), true, `${scenario.name}: ${name} was unexpectedly removed`);
        }
        for (const cookie of cookies.filter(({ name }) => name.startsWith('waooaw.logout-'))) {
          assert.equal(cookie.path, '/api/auth/keycloak-logout');
          assert.equal(cookie.httpOnly, true);
          assert.equal(cookie.secure, true);
          assert.equal(cookie.sameSite, 'Lax');
        }
        if (step.anonymous) {
          const cookieHeader = cookies.map(({ name, value }) => `${name}=${value}`).join('; ');
          const token = await getToken({
            req: {
              cookies: Object.fromEntries(cookies.map(({ name, value }) => [name, value])),
              headers: { cookie: cookieHeader },
            },
            secret,
            secureCookie: true,
          });
          assert.equal(token, null, `${scenario.name}: retained JWT still authenticates after logout`);
        }
      }
    } finally {
      await context.close();
    }
  }
  process.stdout.write(JSON.stringify({ browserName, passed: scenarios.length }));
} finally {
  await browser?.close();
  await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
  rmSync(directory, { recursive: true, force: true });
}
