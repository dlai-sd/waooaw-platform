// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R001, WC171-R002, WC171-R004
// Constitutional basis: C-001, C-042, C-059, C-063

export type MenuIcon =
  | 'agents'
  | 'marketplace'
  | 'alerts'
  | 'settings'
  | 'operations'
  | 'vault'
  | 'pricing'
  | 'providers'
  | 'access'
  | 'founder';

export type MenuLink = { id: string; href: string; label: string; icon: MenuIcon };

export type PlatformLabels = { myAgents: string; marketplace: string; alerts: string; settings: string };

export type GrantFlags = {
  showAccess?: boolean;
  showKeyVaultAdmin?: boolean;
  showPricingAdmin?: boolean;
  showProviderAdmin?: boolean;
  showOperations?: boolean;
};

// The global menu is the same for every customer and every agent: platform concerns only, never a staff link.
export function platformMenu(labels: PlatformLabels): MenuLink[] {
  return [
    { id: 'agents', href: '/professionals/mine', label: labels.myAgents, icon: 'agents' },
    { id: 'marketplace', href: '/marketplace', label: labels.marketplace, icon: 'marketplace' },
    { id: 'alerts', href: '/alerts', label: labels.alerts, icon: 'alerts' },
    { id: 'settings', href: '/settings', label: labels.settings, icon: 'settings' },
  ];
}

// Staff tools live in their own group, shown only for the grants the Business Platform confirmed.
export function operationsMenu(flags: GrantFlags): MenuLink[] {
  return [
    ...(flags.showOperations
      ? [{ id: 'operations', href: '/admin/operations', label: 'Operations', icon: 'operations' as const }]
      : []),
    ...(flags.showPricingAdmin
      ? [{ id: 'pricing', href: '/admin/pricing', label: 'Pricing', icon: 'pricing' as const }]
      : []),
    ...(flags.showProviderAdmin
      ? [
          { id: 'providers', href: '/admin/providers', label: 'Providers', icon: 'providers' as const },
          {
            id: 'agent-operation',
            href: '/admin/agent-operation',
            label: 'Agent operation',
            icon: 'providers' as const,
          },
        ]
      : []),
    ...(flags.showKeyVaultAdmin
      ? [{ id: 'vault', href: '/admin/azure-key-vault', label: 'Azure Key Vault', icon: 'vault' as const }]
      : []),
    ...(flags.showAccess ? [{ id: 'access', href: '/access', label: 'Access', icon: 'access' as const }] : []),
  ];
}

export function founderMenu(founderHome: string): MenuLink[] {
  return [
    { id: 'founder', href: '/founder', label: founderHome, icon: 'founder' },
    { id: 'access', href: '/founder/access', label: 'Access', icon: 'access' },
  ];
}

// The context menu of a chosen agent: the same platform surfaces, in the same order and words, for every agent.
export const FIXED_SURFACES = [
  'overview',
  'plan',
  'decisions',
  'work',
  'results',
  'usage',
  'alerts',
  'rights',
] as const;
export type FixedSurfaceId = (typeof FIXED_SURFACES)[number];

// Every tab the workbench had before WC-171 still opens, so no function is lost.
export const LEGACY_TOOL_SURFACE = {
  overview: 'overview',
  goals: 'plan',
  capabilities: 'usage',
  decisions: 'decisions',
  monitor: 'results',
  work: 'work',
  wallet: 'usage',
  evidence: 'rights',
} as const satisfies Record<string, FixedSurfaceId>;

export type DeclaredEntry = {
  entryId: string;
  labelKey: string;
  label: string;
  icon: string;
  order: number;
  surfaceKind: string;
  target?: string | null;
  blocks: string[];
  available: boolean;
};

export type ContextSurface = { id: string; kind: 'fixed' | 'declared' };

export function declaredSurfaceId(entryId: string): string {
  return `entry-${entryId.toLowerCase().replaceAll('_', '-')}`;
}

export function contextSurfaces(declared: readonly DeclaredEntry[] | undefined): ContextSurface[] {
  return [
    ...FIXED_SURFACES.map((id) => ({ id, kind: 'fixed' as const })),
    ...[...(declared ?? [])]
      .sort((left, right) => left.order - right.order || left.entryId.localeCompare(right.entryId))
      .map((entry) => ({ id: declaredSurfaceId(entry.entryId), kind: 'declared' as const })),
  ];
}

// A deep link names a surface; an unknown or unavailable one falls back to the overview instead of an empty screen.
export function resolveSurface(
  requested: string | null | undefined,
  declared: readonly DeclaredEntry[] | undefined
): string {
  if (!requested) return 'overview';
  const surfaces = contextSurfaces(declared);
  if (!surfaces.some((surface) => surface.id === requested)) return 'overview';
  const entry = (declared ?? []).find((item) => declaredSurfaceId(item.entryId) === requested);
  return entry && !entry.available ? 'overview' : requested;
}
