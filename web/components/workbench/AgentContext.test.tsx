// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R002, WC171-R004
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { fireEvent, render, screen, within } from '@testing-library/react';
import { workbenchMessages } from '@/lib/workbench-i18n';
import type { DeclaredEntry } from '@/lib/navigation-model';
import { blocksForEntry, DeclaredSurface } from './DeclaredSurface';
import { WorkbenchShell } from './WorkbenchShell';
import { relationshipId, snapshotFixture } from './workbench-test-data';

jest.mock('@/components/connections/ConnectionsWorkspace', () => ({
  ConnectionsWorkspace: () => <p>Connected accounts view</p>,
}));
jest.mock('@/components/portal/AlertInbox', () => ({
  AlertInbox: ({ relationshipId: id }: { relationshipId?: string }) => <p>Agent alerts for {id}</p>,
}));

const copy = workbenchMessages('en');

const declared = (overrides: Partial<DeclaredEntry>): DeclaredEntry => ({
  entryId: 'PROFILE_AND_MATURITY',
  labelKey: 'NAV_PROFILE_AND_MATURITY',
  label: 'Profile and maturity',
  icon: 'profile',
  order: 10,
  surfaceKind: 'DOMAIN_BLOCK',
  target: 'SUMMARY_BLOCK',
  blocks: [],
  available: true,
  ...overrides,
});

const block = (id: string, type: string, text = id) =>
  ({ id, type, version: 1, sensitivity: 'LOW', data: { text }, fallback: [{ type: 'TEXT', data: { text } }] }) as never;

function withNavigation(navigation: DeclaredEntry[], blocks: unknown[] = []) {
  const snapshot = snapshotFixture();
  snapshot.projection = { ...snapshot.projection, navigation, blocks } as never;
  return snapshot;
}

describe('agent context menu with declared entries', () => {
  afterEach(() => window.history.replaceState(null, '', '/'));

  it('shows fixed surfaces first and the agent’s own entries after them under their own heading', () => {
    render(
      <WorkbenchShell
        copy={copy}
        initial={withNavigation([
          declared({}),
          declared({
            entryId: 'PLATFORM_ACCOUNTS',
            label: 'Platform accounts',
            order: 30,
            surfaceKind: 'KERNEL_VIEW',
            target: 'connections',
          }),
        ])}
        relationshipId={relationshipId}
      />
    );
    const menu = screen.getByRole('navigation', { name: copy.agentMenuLabel });
    const buttons = within(menu).getAllByRole('button');
    expect(buttons.slice(0, 8).map((button) => button.getAttribute('data-surface'))).toEqual([
      'overview',
      'plan',
      'decisions',
      'work',
      'results',
      'usage',
      'alerts',
      'rights',
    ]);
    expect(buttons.slice(8).map((button) => button.textContent)).toEqual(['Profile and maturity', 'Platform accounts']);
    expect(within(menu).getByText(copy.declaredMenuLabel)).toBeInTheDocument();
  });

  it('opens a declared kernel view and records the surface in the address so a link can reopen it', () => {
    render(
      <WorkbenchShell
        copy={copy}
        initial={withNavigation([
          declared({
            entryId: 'PLATFORM_ACCOUNTS',
            label: 'Platform accounts',
            surfaceKind: 'KERNEL_VIEW',
            target: 'connections',
          }),
        ])}
        relationshipId={relationshipId}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Platform accounts' }));
    expect(screen.getByText('Connected accounts view')).toBeInTheDocument();
    expect(window.location.search).toBe('?surface=entry-platform-accounts');
  });

  it('opens the surface a deep link names, and falls back to the overview for an unknown one', () => {
    const { unmount } = render(
      <WorkbenchShell
        copy={copy}
        initial={withNavigation([])}
        initialSurface="alerts"
        relationshipId={relationshipId}
      />
    );
    expect(screen.getByText(`Agent alerts for ${relationshipId}`)).toBeInTheDocument();
    unmount();
    render(
      <WorkbenchShell
        copy={copy}
        initial={withNavigation([])}
        initialSurface="no-such-surface"
        relationshipId={relationshipId}
      />
    );
    expect(screen.getByRole('button', { name: copy.toolOverview })).toHaveAttribute('aria-current', 'page');
  });

  it('shows an entry that is not available yet as a plain notice, never an empty screen', () => {
    render(
      <WorkbenchShell
        copy={copy}
        initial={withNavigation([declared({ available: false })])}
        relationshipId={relationshipId}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Profile and maturity' }));
    expect(screen.getByText(copy.declaredNotAvailable)).toBeInTheDocument();
  });

  it('serves a second profession with different entries through the same component', () => {
    render(
      <WorkbenchShell
        copy={copy}
        initial={withNavigation([declared({ entryId: 'LESSON_PLANS', label: 'Lesson plans', icon: 'plan' })])}
        relationshipId={relationshipId}
      />
    );
    expect(screen.getByRole('button', { name: 'Lesson plans' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Profile and maturity' })).not.toBeInTheDocument();
  });
});

describe('DeclaredSurface', () => {
  it('draws a registered domain block by its id and a composition by its block types only', () => {
    const blocks = [block('SUMMARY_BLOCK', 'DOMAIN'), block('m1', 'METRIC'), block('t1', 'TEXT')];

    expect(blocksForEntry(declared({}), blocks).map((item) => item.id)).toEqual(['SUMMARY_BLOCK']);
    expect(
      blocksForEntry(
        declared({ surfaceKind: 'BLOCK_COMPOSITION', target: null, blocks: ['METRIC', 'STATUS'] }),
        blocks
      ).map((item) => item.id)
    ).toEqual(['m1']);
    expect(blocksForEntry(declared({ surfaceKind: 'KERNEL_VIEW', target: 'connections' }), blocks)).toEqual([]);
  });

  it('says there is nothing yet and offers the Work surface instead of a blank page', () => {
    const open = jest.fn();
    render(<DeclaredSurface blocks={[]} copy={copy} entry={declared({})} onOpenWork={open} />);
    expect(screen.getByText(copy.declaredNothingYet)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: copy.toolWork }));
    expect(open).toHaveBeenCalledTimes(1);
  });
});
