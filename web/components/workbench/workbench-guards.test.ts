/** @jest-environment node */
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const directories = [join(__dirname), join(__dirname, '..', '..', 'lib')];

function sources() {
  return directories.flatMap((directory) =>
    readdirSync(directory)
      .filter((name) => /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) && !name.includes('test-data'))
      .filter((name) => directory === directories[0] || name.startsWith('workbench'))
      .map((name) => ({ name, text: readFileSync(join(directory, name), 'utf8') }))
  );
}

describe('workbench is common to every professional', () => {
  it('names no profession or marketing specifics in its shipped sources', () => {
    const forbidden =
      /digital[- ]marketing|marketing agent|campaign|social media|linkedin|instagram|whatsapp template|seo\b/i;
    for (const source of sources()) {
      expect({ file: source.name, match: forbidden.exec(source.text)?.[0] ?? null }).toEqual({
        file: source.name,
        match: null,
      });
    }
  });

  it('never writes unsanitised markup', () => {
    for (const source of sources()) {
      expect({ file: source.name, raw: /dangerouslySetInnerHTML|innerHTML\s*=/.test(source.text) }).toEqual({
        file: source.name,
        raw: false,
      });
    }
  });

  it('carries the C-059 implementation header on every shipped source', () => {
    for (const source of sources()) {
      expect({ file: source.name, header: /Implements: work-contracts\/WC-136-/.test(source.text) }).toEqual({
        file: source.name,
        header: true,
      });
    }
  });
});
