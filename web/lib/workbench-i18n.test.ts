// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability), C-063

import { labelFor, plainWords, workbenchMessages, type WorkbenchMessages } from './workbench-i18n';

function keysOf(value: object, prefix = ''): string[] {
  return Object.entries(value).flatMap(([key, item]) =>
    typeof item === 'object' && item !== null ? keysOf(item, `${prefix}${key}.`) : [`${prefix}${key}`]
  );
}

function leaves(value: object): string[] {
  return Object.values(value).flatMap((item) =>
    typeof item === 'object' && item !== null ? leaves(item) : [String(item)]
  );
}

describe('workbench messages', () => {
  it('gives Hindi every user-visible string the English copy has, none of them empty', () => {
    const english = workbenchMessages('en');
    const hindi = workbenchMessages('hi');

    expect(keysOf(hindi).sort()).toEqual(keysOf(english).sort());
    expect(leaves(hindi).every((text) => text.trim().length > 0)).toBe(true);
    expect(hindi.title).not.toBe(english.title);
  });

  it('translates every English sentence, so no Hindi message is the English one', () => {
    const english = workbenchMessages('en') as WorkbenchMessages;
    const hindi = workbenchMessages('hi') as WorkbenchMessages;
    const sentences = (Object.keys(english) as Array<keyof WorkbenchMessages>).filter(
      (key) => typeof english[key] === 'string' && (english[key] as string).split(' ').length > 3
    );

    expect(sentences.length).toBeGreaterThan(10);
    for (const key of sentences) expect(hindi[key]).not.toBe(english[key]);
  });

  it('falls back to English for a locale without workbench copy', () => {
    expect(workbenchMessages('ta')).toBe(workbenchMessages('en'));
  });

  it('shows an undeclared identifier as plain words rather than raw', () => {
    expect(plainWords('WAITING_ON_PLATFORM')).toBe('Waiting on platform');
    expect(plainWords('___')).toBe('___');
    expect(labelFor({ ACTIVE: 'Active' }, 'ACTIVE')).toBe('Active');
    expect(labelFor({ ACTIVE: 'Active' }, 'SOME_NEW_STATE')).toBe('Some new state');
  });
});
