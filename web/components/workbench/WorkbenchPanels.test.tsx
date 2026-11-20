// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { workbenchMessages } from '@/lib/workbench-i18n';
import { CapabilitiesPanel } from './CapabilitiesPanel';
import { ControlsBar } from './ControlsBar';
import { DecisionQueue } from './DecisionQueue';
import { EvidencePanel } from './EvidencePanel';
import { MonitorPanel } from './MonitorPanel';
import { OverviewPanel } from './OverviewPanel';
import { StartPanel } from './StartPanel';
import { WalletPanel } from './WalletPanel';
import { fakeResponse, present, relationshipId, snapshotFixture } from './workbench-test-data';

const copy = workbenchMessages('en');
const base = `/api/relationships/${relationshipId}/workbench`;

type Sent = { path: string; body: Record<string, unknown> };

function accept(response: () => Response = () => fakeResponse(200, { schemaVersion: '1.0', status: 'ACCEPTED' })) {
  const sent: Sent[] = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    sent.push({ path: String(input).slice(base.length), body: JSON.parse(String(init?.body ?? '{}')) });
    return response();
  }) as jest.Mock;
  return sent;
}

function props(snapshot = snapshotFixture()) {
  return { relationshipId, snapshot, copy, onChanged: jest.fn(async () => undefined) };
}

function withCommand(
  snapshot: ReturnType<typeof snapshotFixture>,
  commandId: string,
  enabled: boolean,
  disabledReason?: string
) {
  snapshot.projection.availableCommands = snapshot.projection.availableCommands.map((item) =>
    item.commandId === commandId ? { ...item, enabled, disabledReason } : item
  );
  return snapshot;
}

describe('workbench panels', () => {
  afterEach(() => jest.restoreAllMocks());

  describe('OverviewPanel', () => {
    it('shows the next step, the facts the customer needs and the agent limitations', () => {
      render(<OverviewPanel {...props()} />);
      expect(screen.getByText('Review a decision')).toBeInTheDocument();
      expect(screen.getByText('Your allowance is running low.')).toBeInTheDocument();
      expect(screen.getByText('Performance figures lag by one day.')).toBeInTheDocument();
      expect(screen.getByText('Welcome back.')).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: copy.startGoal })).toBeInTheDocument();
    });

    it('says nothing is needed and omits empty sections', () => {
      const snapshot = snapshotFixture();
      snapshot.projection.recommendedNextAction = undefined;
      snapshot.projection.alerts = [];
      snapshot.projection.limitations = [];
      snapshot.projection.blocks = [];
      render(<OverviewPanel {...props(snapshot)} />);
      expect(screen.getByText(copy.nothingNeeded)).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: copy.alerts })).not.toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: copy.limitations })).not.toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: copy.startGoal })).not.toBeInTheDocument();
    });
  });

  describe('StartPanel', () => {
    it('is hidden once a goal exists', () => {
      const snapshot = snapshotFixture();
      snapshot.projection.currentGoalRef = 'goal-1';
      const { container } = render(<StartPanel {...props(snapshot)} />);
      expect(container).toBeEmptyDOMElement();
    });

    it.each([
      ['a form that is not a goal form', { formId: 'other:grow', fields: [{ fieldId: 'a', label: 'A' }] }, 1],
      [
        'a newer block version than this page understands',
        { formId: 'goal:grow', fields: [{ fieldId: 'a', label: 'A' }] },
        2,
      ],
      ['a form without fields', { formId: 'goal:grow', fields: 'none' }, 1],
      ['a form whose fields are all malformed', { formId: 'goal:grow', fields: [{ fieldId: 1 }, null] }, 1],
    ])('draws nothing for %s', (_name, data, version) => {
      const snapshot = snapshotFixture();
      snapshot.projection.blocks = [
        { id: 'f', type: 'FORM', version, sensitivity: 'CUSTOMER', data, fallback: [] } as never,
      ];
      const { container } = render(<StartPanel {...props(snapshot)} />);
      expect(container).toBeEmptyDOMElement();
    });

    it('explains why a goal cannot be started yet and does not allow sending', () => {
      const snapshot = withCommand(snapshotFixture(), 'create_goal', false, 'Finish the agreement first.');
      render(<StartPanel {...props(snapshot)} />);
      expect(screen.getByText('Finish the agreement first.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: copy.saveGoal })).toBeDisabled();
    });

    it('falls back to the plain unavailable message when no reason is given', () => {
      const snapshot = withCommand(snapshotFixture(), 'create_goal', false);
      render(<StartPanel {...props(snapshot)} />);
      expect(screen.getByText(copy.problems.WORKBENCH_UNAVAILABLE)).toBeInTheDocument();
    });
  });

  describe('MonitorPanel', () => {
    it('shows a tile without a trend or target and hides the alerts section when there are none', () => {
      const snapshot = snapshotFixture();
      snapshot.projection.tiles = [{ ...snapshot.projection.tiles[0], trend: undefined, target: undefined }];
      snapshot.projection.alerts = [];
      render(<MonitorPanel {...props(snapshot)} />);
      expect(screen.getByText('Reach this week')).toBeInTheDocument();
      expect(screen.queryByRole('img')).not.toBeInTheDocument();
      expect(screen.queryByText(new RegExp(`${copy.target}:`))).not.toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: copy.alerts })).not.toBeInTheDocument();
    });

    it('says plainly when there are no tiles and no work items', () => {
      const snapshot = snapshotFixture();
      snapshot.projection.tiles = [];
      snapshot.workItems = { schemaVersion: '1.0', items: [] } as never;
      render(<MonitorPanel {...props(snapshot)} />);
      expect(screen.getByText(copy.noTiles)).toBeInTheDocument();
      expect(screen.getByText(copy.noWorkItems)).toBeInTheDocument();
    });

    it('reports work items as unavailable rather than empty when they could not be read', () => {
      const snapshot = snapshotFixture();
      snapshot.workItems = null;
      render(<MonitorPanel {...props(snapshot)} />);
      expect(screen.getByText(copy.problems.WORKBENCH_UNAVAILABLE)).toBeInTheDocument();
      expect(screen.queryByText(copy.noWorkItems)).not.toBeInTheDocument();
    });
  });

  describe('DecisionQueue', () => {
    it('defers a decision against its own version', async () => {
      const sent = accept();
      const panel = props();
      render(<DecisionQueue {...panel} />);
      fireEvent.click(screen.getByRole('button', { name: copy.defer }));
      await waitFor(() => expect(panel.onChanged).toHaveBeenCalled());
      expect(sent[0]).toEqual({
        path: '/decisions/decision-1/resolve',
        body: { schemaVersion: '1.0', expectedVersion: 'decision-version-3', resolution: 'DEFER' },
      });
      expect(screen.getByText('One publishing credit')).toBeInTheDocument();
      expect(screen.getByText('2026-06-02')).toBeInTheDocument();
    });

    it('says when nothing is waiting', () => {
      const snapshot = snapshotFixture();
      snapshot.projection.decisions = [];
      render(<DecisionQueue {...props(snapshot)} />);
      expect(screen.getByText(copy.noDecisions)).toBeInTheDocument();
    });

    it('omits cost and expiry that were not given and disables answers the customer may not give', () => {
      const snapshot = withCommand(snapshotFixture(), 'resolve_decision', false, 'Only the owner can decide.');
      snapshot.projection.decisions = [{ ...snapshot.projection.decisions[0], cost: undefined, expiresAt: undefined }];
      render(<DecisionQueue {...props(snapshot)} />);
      expect(screen.queryByText(copy.cost)).not.toBeInTheDocument();
      expect(screen.queryByText(copy.expires)).not.toBeInTheDocument();
      expect(screen.getByText('Only the owner can decide.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Approve publish' })).toBeDisabled();
      expect(screen.getByRole('button', { name: copy.defer })).toBeDisabled();
    });
  });

  describe('EvidencePanel', () => {
    it('requests a JSON export', async () => {
      const sent = accept(() => fakeResponse(202, { schemaVersion: '1.0', status: 'ACCEPTED' }));
      render(<EvidencePanel {...props()} />);
      fireEvent.click(screen.getByRole('button', { name: `${copy.exportEvidence} (JSON)` }));
      expect(await screen.findByText(copy.exportRequested)).toBeInTheDocument();
      expect(sent[0].body).toMatchObject({ scope: 'RELATIONSHIP', format: 'JSON' });
    });

    it('distinguishes an empty list from one that could not be read', () => {
      const empty = snapshotFixture();
      empty.evidence = { schemaVersion: '1.0', evidenceState: 'AVAILABLE', items: [] } as never;
      const first = render(<EvidencePanel {...props(empty)} />);
      expect(screen.getByText(copy.noEvidence)).toBeInTheDocument();
      first.unmount();

      const unread = snapshotFixture();
      unread.evidence = null;
      render(<EvidencePanel {...props(unread)} />);
      expect(screen.getByText(copy.problems.WORKBENCH_UNAVAILABLE)).toBeInTheDocument();
      expect(screen.queryByText(copy.noEvidence)).not.toBeInTheDocument();
    });

    it('explains why an export is not offered', () => {
      const snapshot = withCommand(snapshotFixture(), 'export_evidence', false, 'Exports open after the first report.');
      render(<EvidencePanel {...props(snapshot)} />);
      expect(screen.getByText('Exports open after the first report.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: `${copy.exportEvidence} (PDF)` })).toBeDisabled();
      expect(screen.getByRole('button', { name: `${copy.exportEvidence} (JSON)` })).toBeDisabled();
    });
  });

  describe('CapabilitiesPanel', () => {
    function twoCapabilities() {
      const snapshot = snapshotFixture();
      snapshot.capabilities = {
        schemaVersion: '1.0',
        items: [
          {
            skillId: 'alpha',
            label: 'Alpha',
            availability: 'AVAILABLE',
            state: 'ACTIVE',
            approvalMode: 'ASK_FIRST',
            componentIds: ['posts', 'mystery_box'],
            nextRunMeaning: 'Tomorrow at 9',
          },
          {
            skillId: 'beta',
            label: 'Beta',
            availability: 'AVAILABLE',
            state: 'PAUSED',
            approvalMode: 'AUTO',
            componentIds: [],
          },
        ],
      } as never;
      return snapshot;
    }

    it('pauses an active capability and resumes a paused one', async () => {
      const sent = accept();
      render(<CapabilitiesPanel {...props(twoCapabilities())} />);
      expect(screen.getByText(/Tomorrow at 9/)).toBeInTheDocument();
      expect(screen.getByText(/Posts, /)).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: `${copy.pause} Alpha` }));
      await waitFor(() => expect(sent).toHaveLength(1));
      await screen.findByText(copy.done);
      fireEvent.click(await screen.findByRole('button', { name: `${copy.resume} Beta` }));
      await waitFor(() => expect(sent).toHaveLength(2));
      expect(sent.map((item) => [item.path, item.body.command])).toEqual([
        ['/capabilities/alpha/commands', 'PAUSE'],
        ['/capabilities/beta/commands', 'RESUME'],
      ]);
    });

    it('disables every capability command and says why when changes are not permitted', () => {
      const snapshot = withCommand(twoCapabilities(), 'change_capability', false, 'Changes are locked during review.');
      render(<CapabilitiesPanel {...props(snapshot)} />);
      expect(screen.getByText('Changes are locked during review.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: `${copy.pause} Alpha` })).toBeDisabled();
      expect(screen.getByRole('button', { name: `${copy.resume} Beta` })).toBeDisabled();
    });

    it('distinguishes an empty list from one that could not be read', () => {
      const empty = snapshotFixture();
      empty.capabilities = { schemaVersion: '1.0', items: [] } as never;
      const first = render(<CapabilitiesPanel {...props(empty)} />);
      expect(screen.getByText(copy.noCapabilities)).toBeInTheDocument();
      first.unmount();

      const unread = snapshotFixture();
      unread.capabilities = null;
      render(<CapabilitiesPanel {...props(unread)} />);
      expect(screen.getByText(copy.problems.WORKBENCH_UNAVAILABLE)).toBeInTheDocument();
    });
  });

  describe('WalletPanel', () => {
    it('reports an unavailable allowance without inventing figures', () => {
      const snapshot = snapshotFixture();
      snapshot.wallet = null;
      render(<WalletPanel {...props(snapshot)} />);
      expect(screen.getByText(copy.problems.SPEND_COMMERCIAL_UNAVAILABLE)).toBeInTheDocument();
    });

    it('says when the package has no allowance components', () => {
      const snapshot = snapshotFixture();
      snapshot.wallet = { ...present(snapshot.wallet), components: [] };
      render(<WalletPanel {...props(snapshot)} />);
      expect(screen.getByText(copy.noComponents)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: copy.topUp })).not.toBeInTheDocument();
    });

    it('does not offer a top-up the service says is unavailable', () => {
      const snapshot = snapshotFixture();
      snapshot.wallet = { ...present(snapshot.wallet), topUpAvailable: false };
      render(<WalletPanel {...props(snapshot)} />);
      expect(screen.getByText(/4 \/ 10/)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: copy.topUp })).not.toBeInTheDocument();
    });

    it('disables a top-up the plan does not allow and says why', () => {
      const snapshot = withCommand(snapshotFixture(), 'top_up', false, 'Top-ups are paused.');
      render(<WalletPanel {...props(snapshot)} />);
      expect(screen.getByText('Top-ups are paused.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: copy.topUp })).toBeDisabled();
    });

    it('sends the chosen component and quantity', async () => {
      const sent = accept(() =>
        fakeResponse(200, {
          schemaVersion: '1.0',
          operationRef: 'op',
          status: 'PENDING_PAYMENT',
          priceInclGstPaise: 5900,
        })
      );
      const snapshot = snapshotFixture();
      snapshot.wallet = {
        ...present(snapshot.wallet),
        components: [
          ...present(snapshot.wallet).components,
          { componentId: 'comments', label: 'Comments', remaining: 1, quantity: 5, periodEnd: '2026-06-30T00:00:00Z' },
        ],
      };
      render(<WalletPanel {...props(snapshot)} />);
      fireEvent.change(screen.getByLabelText(copy.topUpComponent), { target: { value: 'comments' } });
      fireEvent.change(screen.getByLabelText(copy.topUpQuantity), { target: { value: '3' } });
      fireEvent.click(screen.getByRole('button', { name: copy.topUp }));
      expect(await screen.findByText(/59\.00/)).toBeInTheDocument();
      expect(sent[0]).toEqual({
        path: '/topups',
        body: { schemaVersion: '1.0', expectedVersion: 'relationship-7', componentId: 'comments', quantity: 3 },
      });
    });

    it('shows no receipt when the request is refused and says so', async () => {
      accept(() => fakeResponse(503, { code: 'SPEND_COMMERCIAL_UNAVAILABLE' }));
      render(<WalletPanel {...props()} />);
      fireEvent.click(screen.getByRole('button', { name: copy.topUp }));
      expect(await screen.findByRole('alert')).toHaveTextContent(copy.problems.SPEND_COMMERCIAL_UNAVAILABLE);
      expect(screen.queryByText(/₹/)).not.toBeInTheDocument();
    });
  });

  describe('ControlsBar', () => {
    it('pauses the work against the current version', async () => {
      const sent = accept();
      const panel = props();
      render(<ControlsBar {...panel} />);
      fireEvent.click(screen.getByRole('button', { name: copy.pauseWork }));
      await waitFor(() => expect(panel.onChanged).toHaveBeenCalled());
      expect(sent[0]).toEqual({
        path: '/controls/pause',
        body: { schemaVersion: '1.0', expectedVersion: 'relationship-7' },
      });
    });

    it('disables pause when it is not permitted but leaves Stop available', () => {
      render(<ControlsBar {...props(withCommand(snapshotFixture(), 'pause', false))} />);
      expect(screen.getByRole('button', { name: copy.pauseWork })).toBeDisabled();
      expect(screen.getByRole('button', { name: copy.stop })).toBeEnabled();
    });

    it('returns focus to Stop when the confirmation is cancelled with the button', () => {
      render(<ControlsBar {...props()} />);
      fireEvent.click(screen.getByRole('button', { name: copy.stop }));
      fireEvent.click(screen.getByRole('button', { name: copy.cancel }));
      expect(screen.queryByRole('button', { name: copy.stopConfirm })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: copy.stop })).toHaveFocus();
    });
  });
});
