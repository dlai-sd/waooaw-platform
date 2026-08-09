// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-04, §UX-PRIV-01
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { safeReturnTarget } from './safe-return';

describe('safe return targets', () => {
  it.each(['https://attacker.test', '//attacker.test', '/api/auth/signout', '/founder', '/relationships/../founder'])('rejects %s', (target) => {
    expect(safeReturnTarget(target)).toBe('/home');
  });

  it.each(['/home', '/settings', '/professionals/mine', '/relationships/8f6f7550-98c7-4a8f-bd63-36f07ee15c9d'])('accepts %s', (target) => {
    expect(safeReturnTarget(target)).toBe(target);
  });
});