// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R001, WC171-R002, WC171-R004
// Constitutional basis: C-001, C-042, C-059, C-063

import {
  contextSurfaces,
  declaredSurfaceId,
  FIXED_SURFACES,
  founderMenu,
  LEGACY_TOOL_SURFACE,
  operationsMenu,
  platformMenu,
  resolveSurface,
  type DeclaredEntry,
} from './navigation-model';

const labels = { myAgents: 'My Agents', marketplace: 'Marketplace', alerts: 'Alerts', settings: 'Settings' };

const entry = (overrides: Partial<DeclaredEntry> = {}): DeclaredEntry => ({
  entryId: 'PROFILE_AND_MATURITY',
  labelKey: 'NAV_PROFILE_AND_MATURITY',
  label: 'Profile and maturity',
  icon: 'profile',
  order: 10,
  surfaceKind: 'DOMAIN_BLOCK',
  target: 'MARKETING_MATURITY_SUMMARY',
  blocks: [],
  available: true,
  ...overrides,
});

describe('the global menu', () => {
  it('is the same four platform links for everyone and carries no staff link', () => {
    expect(platformMenu(labels).map((link) => link.href)).toEqual([
      '/professionals/mine',
      '/marketplace',
      '/alerts',
      '/settings',
    ]);
  });

  it('puts staff tools in their own group, only for the grants held and in a fixed order', () => {
    expect(operationsMenu({})).toEqual([]);
    expect(operationsMenu({ showPricingAdmin: true }).map((link) => link.id)).toEqual(['pricing']);
    expect(
      operationsMenu({
        showAccess: true,
        showKeyVaultAdmin: true,
        showOperations: true,
        showPricingAdmin: true,
        showProviderAdmin: true,
      }).map((link) => link.id)
    ).toEqual(['operations', 'pricing', 'providers', 'agent-operation', 'professionals', 'vault', 'access']);
  });

  it('gives every staff tool its own icon so two entries are never mistaken for each other', () => {
    const tools = operationsMenu({
      showAccess: true,
      showKeyVaultAdmin: true,
      showOperations: true,
      showPricingAdmin: true,
      showProviderAdmin: true,
    });
    expect(new Set(tools.map((link) => link.icon)).size).toBe(tools.length);
    expect(new Set(tools.map((link) => link.label)).size).toBe(tools.length);
  });

  it('keeps the Founder shell to its own links', () => {
    expect(founderMenu('Founder home').map((link) => link.href)).toEqual(['/founder', '/founder/access']);
  });
});

describe('the agent context menu', () => {
  it('has the fixed surfaces in one order for every agent', () => {
    expect(FIXED_SURFACES).toEqual(['overview', 'plan', 'decisions', 'work', 'results', 'usage', 'alerts', 'rights']);
    expect(contextSurfaces(undefined).map((surface) => surface.id)).toEqual([...FIXED_SURFACES]);
    expect(contextSurfaces([]).every((surface) => surface.kind === 'fixed')).toBe(true);
  });

  it('maps every workbench tab that existed before onto a fixed surface, so no function is lost', () => {
    for (const tool of [
      'overview',
      'goals',
      'capabilities',
      'decisions',
      'monitor',
      'work',
      'wallet',
      'evidence',
    ] as const)
      expect(FIXED_SURFACES).toContain(LEGACY_TOOL_SURFACE[tool]);
  });

  it('appends declared entries by order hint after the fixed surfaces', () => {
    const surfaces = contextSurfaces([entry({ entryId: 'SECOND', order: 20 }), entry({ entryId: 'FIRST', order: 5 })]);
    expect(surfaces.slice(-2).map((surface) => surface.id)).toEqual([
      declaredSurfaceId('FIRST'),
      declaredSurfaceId('SECOND'),
    ]);
    expect(surfaces.slice(-2).every((surface) => surface.kind === 'declared')).toBe(true);
  });

  it('serves two professions through the same code', () => {
    const marketing = contextSurfaces([entry()]).slice(-1)[0].id;
    const teaching = contextSurfaces([entry({ entryId: 'LESSON_PLANS', label: 'Lesson plans' })]).slice(-1)[0].id;
    expect(marketing).toBe('entry-profile-and-maturity');
    expect(teaching).toBe('entry-lesson-plans');
  });
});

describe('deep links', () => {
  const declared = [entry(), entry({ entryId: 'LATER', order: 20, available: false })];

  it.each([
    [undefined, 'overview'],
    [null, 'overview'],
    ['decisions', 'decisions'],
    ['rights', 'rights'],
    ['entry-profile-and-maturity', 'entry-profile-and-maturity'],
    ['entry-later', 'overview'],
    ['entry-unknown', 'overview'],
    ['<script>', 'overview'],
  ])('opens %s on %s', (requested, expected) => {
    expect(resolveSurface(requested, declared)).toBe(expected);
  });
});
