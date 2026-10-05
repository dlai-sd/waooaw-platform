/** @jest-environment node */

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { validateSecurityPatches } = require('../scripts/verify-security-patches');

const GHSA = 'GHSA-test-0000-0000';
const PATCH = 'patches/dependency@1.0.0.patch';
const VERIFIER = 'scripts/verify-dependency.js';

const createFixture = () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'security-patches-'));
  fs.mkdirSync(path.join(root, 'patches'));
  fs.mkdirSync(path.join(root, 'scripts'));
  const packageJson = {
    pnpm: {
      patchedDependencies: { 'dependency@1.0.0': PATCH },
      auditConfig: { ignoreGhsas: [GHSA] },
    },
  };
  const policy = {
    schema: 'waooaw.web-security-patches/v1',
    advisories: [
      {
        ghsa: GHSA,
        package: 'dependency',
        version: '1.0.0',
        patch: PATCH,
        verifier: VERIFIER,
      },
    ],
  };
  fs.writeFileSync(path.join(root, 'package.json'), JSON.stringify(packageJson));
  fs.writeFileSync(path.join(root, 'security-patches.json'), JSON.stringify(policy));
  fs.writeFileSync(path.join(root, 'pnpm-lock.yaml'), `dependency@1.0.0:\n  path: ${PATCH}\n`);
  fs.writeFileSync(path.join(root, PATCH), 'diff --git a/file.js b/file.js\n');
  fs.writeFileSync(path.join(root, VERIFIER), "'use strict';\n");
  return { root, packageJson, policy };
};

const writeJson = (root, file, value) => fs.writeFileSync(path.join(root, file), JSON.stringify(value));

afterEach(() => {
  for (const directory of fs.readdirSync(os.tmpdir())) {
    if (directory.startsWith('security-patches-')) {
      fs.rmSync(path.join(os.tmpdir(), directory), {
        recursive: true,
        force: true,
      });
    }
  }
});

test('accepts a complete patch policy with a passing exploit verifier', () => {
  const { root } = createFixture();
  expect(() => validateSecurityPatches(root)).not.toThrow();
});

test('rejects an ignored advisory without an exact policy entry', () => {
  const { root, policy } = createFixture();
  policy.advisories = [];
  writeJson(root, 'security-patches.json', policy);
  expect(() => validateSecurityPatches(root)).toThrow('every ignored GHSA');
});

test('rejects a policy entry without a patched dependency binding', () => {
  const { root, packageJson } = createFixture();
  packageJson.pnpm.patchedDependencies = {};
  writeJson(root, 'package.json', packageJson);
  expect(() => validateSecurityPatches(root)).toThrow('is not bound');
});

test('rejects a patch absent from the frozen lockfile', () => {
  const { root } = createFixture();
  fs.writeFileSync(path.join(root, 'pnpm-lock.yaml'), 'lockfileVersion: 9\n');
  expect(() => validateSecurityPatches(root)).toThrow('absent from the frozen lockfile');
});

test('rejects policy paths outside the Web root', () => {
  const { root, policy } = createFixture();
  policy.advisories[0].patch = '../outside.patch';
  writeJson(root, 'security-patches.json', policy);
  expect(() => validateSecurityPatches(root)).toThrow('inside the Web root');
});

test('rejects an empty patch', () => {
  const { root } = createFixture();
  fs.writeFileSync(path.join(root, PATCH), '  \n');
  expect(() => validateSecurityPatches(root)).toThrow('patch is empty');
});

test('rejects a failing exploit verifier', () => {
  const { root } = createFixture();
  fs.writeFileSync(path.join(root, VERIFIER), 'process.exit(1);\n');
  expect(() => validateSecurityPatches(root)).toThrow('exploit regression failed');
});
