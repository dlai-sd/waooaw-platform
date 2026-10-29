/** @jest-environment node */

import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

// Sign-in is deliberately outside WC-126. Keep this explicit, not a wildcard
// exemption for future server modules.
const signInFiles = new Set([
  'lib/auth.ts',
  'lib/auth-abuse-limiter.ts',
  'lib/auth-transition.ts',
  'lib/identity-security-events.ts',
  'lib/oidc-transaction.ts',
  'lib/safe-return.ts',
  'lib/server-diagnostics.ts',
]);
const inputParsers: Record<string, string[]> = {
  'lib/consent.ts': ['parseConsentCookie'],
  'lib/same-origin-request.ts': ['normalizedOrigin'],
  'lib/key-vault-admin.ts': ['claimsFromToken'],
  'app/api/admin/azure-key-vault/route.ts': ['sameOrigin'],
  'app/api/acquisition/events/route.ts': ['POSTHandler'],
  'config/public-config.ts': ['validatePublicConfiguration'],
};
const owners = new Set([
  'logServerFailure',
  'identityProblem',
  'conversationProblem',
  'voiceProblem',
  'describePortalFailure',
]);

function callsOwner(node: ts.Node): boolean {
  if (ts.isBlock(node)) {
    for (const statement of node.statements) {
      if (callsOwner(statement)) return true;
      if (ts.isReturnStatement(statement) || ts.isThrowStatement(statement)) return false;
    }
    return false;
  }
  if (ts.isIfStatement(node)) return false;
  if (ts.isFunctionLike(node)) return false;
  if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && owners.has(node.expression.text)) return true;
  return ts.forEachChild(node, callsOwner) === true;
}

function ownerName(node: ts.Node): string {
  for (let parent = node.parent; parent; parent = parent.parent) {
    if (ts.isFunctionDeclaration(parent)) return parent.name?.text ?? '';
  }
  return '';
}

function inputOnlyTry(node: ts.Node, source: ts.SourceFile): boolean {
  let valid = true;
  function check(child: ts.Node) {
    if (ts.isCallExpression(child)) {
      const call = child.expression.getText(source);
      if (
        ![
          'request.json',
          'readRequestJson',
          'JSON.parse',
          'decodeURIComponent',
          'Buffer.from',
          'String',
          'errors.push',
        ].includes(call) &&
        !/\.(startsWith|toString|split)$/.test(call)
      )
        valid = false;
    }
    if (ts.isNewExpression(child) && !['URL', 'Error'].includes(child.expression.getText(source))) valid = false;
    ts.forEachChild(child, check);
  }
  check(node);
  return valid;
}

function policyViolations(file: string, text: string): string[] {
  const source = ts.createSourceFile(
    file,
    text,
    ts.ScriptTarget.Latest,
    true,
    file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );
  if (
    source.statements.some(
      (statement) =>
        ts.isExpressionStatement(statement) &&
        ts.isStringLiteral(statement.expression) &&
        statement.expression.text === 'use client'
    )
  )
    return [];
  if (file.startsWith('app/api/auth/') || signInFiles.has(file)) return [];
  const failures: string[] = [];
  function report(node: ts.Node, reason: string) {
    failures.push(`${file}:${source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1} ${reason}`);
  }
  function visit(node: ts.Node) {
    if (ts.isCatchClause(node) && !callsOwner(node.block)) {
      const owner = ownerName(node);
      const allowedInput =
        inputParsers[file]?.includes(owner) &&
        ts.isTryStatement(node.parent) &&
        inputOnlyTry(node.parent.tryBlock, source);
      if (!allowedInput) report(node, 'silent server catch');
    }
    if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
      const name = node.expression.name.text;
      if (
        node.expression.expression.getText(source) === 'console' &&
        ['error', 'warn', 'log'].includes(name) &&
        file !== 'lib/server-failure.ts'
      )
        report(node, 'use logServerFailure, not raw console logging');
      if (name === 'catch') {
        const callback = node.arguments[0];
        const promise = node.expression.expression;
        const inputJson =
          ts.isCallExpression(promise) &&
          ['request.json', 'readRequestJson'].includes(promise.expression.getText(source)) &&
          callback &&
          ts.isArrowFunction(callback) &&
          ['null', 'undefined'].includes(callback.body.getText(source));
        if (
          !inputJson &&
          (!callback ||
            !(ts.isArrowFunction(callback) || ts.isFunctionExpression(callback)) ||
            !callsOwner(callback.body))
        ) {
          report(node, 'silent server promise rejection');
        }
      }
    }
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      ['logServerFailure', 'withServerFailureBoundary', 'readServerResponse'].includes(node.expression.text) &&
      !['lib/server-failure.ts', 'lib/server-failure-boundary.ts'].includes(file)
    ) {
      const event = node.arguments[node.expression.text === 'readServerResponse' ? 1 : 0];
      if (!event || !ts.isStringLiteral(event) || !/^web\.[a-z0-9_]+(?:\.[a-z0-9_]+)*$/.test(event.text)) {
        report(node, 'failure event must be a static, stable web event name');
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  return failures;
}

function serverSources(directory: string): string[] {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) return entry.name === 'generated' ? [] : serverSources(file);
    return /\.tsx?$/.test(file) && !/\.(test|spec)\./.test(file) ? [file] : [];
  });
}

describe('server failure regression policy', () => {
  it('excludes the existing sign-in diagnostic sink, not other server logging', () => {
    const text = 'console.error(error.name); console.warn(error);';
    expect(policyViolations('lib/server-diagnostics.ts', text)).toEqual([]);
    expect(policyViolations('lib/new-server-module.ts', text)).toHaveLength(2);
  });

  it('covers every non-sign-in app and library catch in the existing Jest CI gate', () => {
    const root = path.resolve(__dirname, '..');
    const files = ['app', 'lib', 'components', 'config'].flatMap((directory) =>
      serverSources(path.join(root, directory))
    );
    files.push(...['middleware.ts', 'instrumentation.ts'].map((file) => path.join(root, file)).filter(fs.existsSync));
    const violations = files.flatMap((file) =>
      policyViolations(path.relative(root, file), fs.readFileSync(file, 'utf8'))
    );
    expect(files.length).toBeGreaterThan(100);
    expect(violations).toEqual([]);
  });

  it.each([
    'try { await load(); } catch {}',
    'try { await load(); } catch (error) { console.error(error.name); }',
    'load().catch(() => undefined)',
    'load().catch(function () { return null; })',
    'try { await load(); } catch (error) { const later = () => logServerFailure("web.test.failed", error); }',
    'try { await load(); } catch (error) { if (flag) logServerFailure("web.test.failed", error); }',
    'try { await load(); } catch (error) { return; logServerFailure("web.test.failed", error); }',
    'logServerFailure(userInput, error)',
    'request.json().catch(() => { load(); return null; })',
  ])('rejects new silent or bare-name handling: %s', (text) => {
    expect(policyViolations('lib/new-server-module.ts', text).length).toBeGreaterThan(0);
  });

  it.each([
    "try { await load(); } catch (error) { logServerFailure('web.test.failed', error); }",
    'try { await load(); } catch (error) { const problem = await identityProblem(error); return problem; }',
    "load().catch(error => { logServerFailure('web.test.failed', error); return undefined; })",
    'request.json().catch(() => null)',
  ])('accepts observed failures and input-only rejection: %s', (text) => {
    expect(policyViolations('lib/new-server-module.ts', text)).toEqual([]);
  });
});
