// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-023, C-042, C-059, C-063, ADR-051

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { workbenchMessages } from '@/lib/workbench-i18n';
import { toolForPurpose, WorkbenchShell } from './WorkbenchShell';
import { fakeResponse, present, relationshipId, snapshotFixture } from './workbench-test-data';

const copy = workbenchMessages('en');
const base = `/api/relationships/${relationshipId}/workbench`;

type Call = { method: string; path: string; headers: Record<string, string>; body: Record<string, unknown> | null };

function installFetch(post: (call: Call) => Response, projection = snapshotFixture().projection) {
  const calls: Call[] = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const method = init?.method ?? 'GET';
    const path = String(input).slice(base.length);
    const call: Call = {
      method,
      path,
      headers: (init?.headers ?? {}) as Record<string, string>,
      body: init?.body ? JSON.parse(String(init.body)) : null,
    };
    calls.push(call);
    if (method === 'POST') return post(call);
    if (path === '') return fakeResponse(200, projection, { etag: '"relationship-8"' });
    const fixture = snapshotFixture();
    const bodies: Record<string, unknown> = {
      '/goals': fixture.goals,
      '/plans/current': fixture.plan,
      '/capabilities': fixture.capabilities,
      '/wallet': fixture.wallet,
      '/evidence': fixture.evidence,
      '/work-items': fixture.workItems,
    };
    return path in bodies && bodies[path] !== null
      ? fakeResponse(200, bodies[path])
      : fakeResponse(404, { code: 'WORKBENCH_UNAVAILABLE' });
  }) as jest.Mock;
  return calls;
}

function renderShell(snapshot = snapshotFixture()) {
  return render(<WorkbenchShell copy={copy} initial={snapshot} relationshipId={relationshipId} />);
}

function openTool(name: string) {
  fireEvent.click(
    within(screen.getByRole('navigation', { name: copy.toolsLabel })).getByRole('button', { name: new RegExp(name) })
  );
}

describe('WorkbenchShell', () => {
  afterEach(() => jest.restoreAllMocks());

  it('names its landmarks, lists the tools and always offers Stop', () => {
    renderShell();
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: copy.title })).toBeInTheDocument();
    const rail = within(screen.getByRole('navigation', { name: copy.toolsLabel }));
    expect(rail.getByRole('button', { name: copy.toolOverview })).toHaveAttribute('aria-current', 'page');
    expect(rail.getByRole('button', { name: new RegExp(`${copy.toolDecisions} \\(1\\)`) })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: copy.stop })).toBeEnabled();
    expect(screen.getByText('One decision is waiting.')).toBeInTheDocument();
  });

  it('keeps Stop available when the allowance is exhausted and pause is not permitted', () => {
    const snapshot = snapshotFixture();
    snapshot.wallet = {
      ...present(snapshot.wallet),
      components: [{ ...present(snapshot.wallet).components[0], remaining: 0 }],
    };
    snapshot.projection.availableCommands = snapshot.projection.availableCommands.map((item) =>
      item.commandId === 'pause' ? { ...item, enabled: false } : item
    );
    renderShell(snapshot);
    expect(screen.getByRole('button', { name: copy.stop })).toBeEnabled();
    expect(screen.getByRole('button', { name: copy.pauseWork })).toBeDisabled();
  });

  it('hides the allowance tool from a beneficiary', () => {
    const snapshot = snapshotFixture();
    snapshot.projection.audience = 'beneficiary';
    snapshot.wallet = null;
    renderShell(snapshot);
    const rail = within(screen.getByRole('navigation', { name: copy.toolsLabel }));
    expect(rail.queryByRole('button', { name: copy.toolWallet })).not.toBeInTheDocument();
    expect(rail.getByRole('button', { name: copy.toolEvidence })).toBeInTheDocument();
  });

  it('moves focus to the panel when the tool changes and supports arrow keys in the rail', () => {
    renderShell();
    openTool(copy.toolMonitor);
    expect(screen.getByRole('heading', { name: copy.monitor })).toBeInTheDocument();
    expect(screen.getByText('Reach this week')).toBeInTheDocument();
    expect(screen.getByText('Draft the weekly post', { exact: false })).toBeInTheDocument();
    expect(document.activeElement).toHaveClass('workbench-panel');
    const overview = screen.getByRole('button', { name: copy.toolOverview });
    overview.focus();
    fireEvent.keyDown(overview, { key: 'ArrowDown' });
    expect(screen.getByRole('button', { name: copy.toolGoals })).toHaveFocus();
  });

  it('starts a goal from the declared form with a fresh idempotency key and refreshes', async () => {
    const calls = installFetch(() => fakeResponse(200, { schemaVersion: '1.0', status: 'ACCEPTED' }));
    renderShell();
    fireEvent.change(screen.getByLabelText(copy.goalName), { target: { value: 'Grow reach' } });
    fireEvent.change(screen.getByLabelText('Audience'), { target: { value: 'local shops' } });
    fireEvent.click(screen.getByRole('button', { name: copy.saveGoal }));
    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    const post = present(calls.find((call) => call.method === 'POST'));
    expect(post.path).toBe('/goals');
    expect(post.headers['Idempotency-Key']).toMatch(/[0-9a-f-]{36}/);
    expect(post.body).toEqual({
      schemaVersion: '1.0',
      expectedVersion: 'relationship-7',
      goalTypeId: 'grow',
      title: 'Grow reach',
      parameters: { audience: 'local shops' },
    });
    await waitFor(() => expect(calls.some((call) => call.method === 'GET' && call.path === '')).toBe(true));
    expect(await screen.findByText(copy.done)).toBeInTheDocument();
  });

  it('resolves a decision against the decision version', async () => {
    const calls = installFetch(() => fakeResponse(200, { schemaVersion: '1.0', status: 'ACCEPTED' }));
    renderShell();
    openTool(copy.toolDecisions);
    expect(screen.getByText('Publish the weekly update')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Approve publish' }));
    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    const post = present(calls.find((call) => call.method === 'POST'));
    expect(post.path).toBe('/decisions/decision-1/resolve');
    expect(post.body).toEqual({ schemaVersion: '1.0', expectedVersion: 'decision-version-3', resolution: 'APPROVE' });
  });

  it('asks for a second confirmation before stopping and then sends the stop', async () => {
    const calls = installFetch(() => fakeResponse(200, { schemaVersion: '1.0', status: 'ACCEPTED' }));
    renderShell();
    fireEvent.click(screen.getByRole('button', { name: copy.stop }));
    const confirm = screen.getByRole('button', { name: copy.stopConfirm });
    expect(confirm).toHaveFocus();
    expect(calls.some((call) => call.method === 'POST')).toBe(false);
    fireEvent.click(confirm);
    await waitFor(() => expect(calls.some((call) => call.path === '/controls/stop')).toBe(true));
    expect(present(calls.find((call) => call.path === '/controls/stop')).body).toEqual({
      schemaVersion: '1.0',
      expectedVersion: 'relationship-7',
    });
    await waitFor(() => expect(screen.queryByRole('button', { name: copy.stopConfirm })).not.toBeInTheDocument());
  });

  it('cancels a stop confirmation with Escape and returns focus to Stop', () => {
    renderShell();
    fireEvent.click(screen.getByRole('button', { name: copy.stop }));
    fireEvent.keyDown(screen.getByRole('button', { name: copy.stopConfirm }), { key: 'Escape' });
    expect(screen.queryByRole('button', { name: copy.stopConfirm })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: copy.stop })).toHaveFocus();
  });

  it('enables an available capability and disables an unavailable one with its limitation', async () => {
    const calls = installFetch(() => fakeResponse(200, { schemaVersion: '1.0', status: 'ACCEPTED' }));
    renderShell();
    openTool(copy.toolCapabilities);
    expect(screen.getByText('Reports are not available on this package.')).toBeInTheDocument();
    const buttons = screen.getAllByRole('button', { name: new RegExp(`^${copy.enable}`) });
    expect(buttons[1]).toBeDisabled();
    fireEvent.click(buttons[0]);
    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    const post = present(calls.find((call) => call.method === 'POST'));
    expect(post.path).toBe('/capabilities/weekly-post/commands');
    expect(post.body).toMatchObject({ command: 'ENABLE', expectedVersion: 'relationship-7' });
  });

  it('requests a top-up and shows the receipt in rupees', async () => {
    installFetch(() =>
      fakeResponse(200, {
        schemaVersion: '1.0',
        operationRef: 'op-1',
        status: 'PENDING_PAYMENT',
        componentId: 'posts',
        quantity: 2,
        priceInclGstPaise: 11800,
        basePricePaise: 10000,
        gstPaise: 1800,
        taxTreatment: 'GST_INCLUDED',
        correlationId: 'c',
      })
    );
    renderShell();
    openTool(copy.toolWallet);
    expect(screen.getByText(/4 \/ 10/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(copy.topUpQuantity), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: copy.topUp }));
    expect(await screen.findByText(new RegExp(copy.topUpStates.PENDING_PAYMENT))).toBeInTheDocument();
    expect(screen.getByText(/118\.00/)).toBeInTheDocument();
  });

  it('points a delegate at the account owner instead of offering a top-up', () => {
    const snapshot = snapshotFixture();
    snapshot.wallet = { ...present(snapshot.wallet), askAccountOwner: true, topUpAvailable: false };
    renderShell(snapshot);
    openTool(copy.toolWallet);
    expect(screen.getByText(copy.askAccountOwner)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: copy.topUp })).not.toBeInTheDocument();
  });

  it('requests an evidence export for the relationship', async () => {
    const calls = installFetch(() => fakeResponse(202, { schemaVersion: '1.0', status: 'ACCEPTED' }));
    renderShell();
    openTool(copy.toolEvidence);
    expect(screen.getByText(/Weekly post published/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: `${copy.exportEvidence} (PDF)` }));
    await waitFor(() => expect(calls.some((call) => call.method === 'POST')).toBe(true));
    expect(present(calls.find((call) => call.method === 'POST')).body).toMatchObject({
      scope: 'RELATIONSHIP',
      format: 'PDF',
    });
    expect(await screen.findByText(copy.exportRequested)).toBeInTheDocument();
  });

  it('refreshes after a version conflict and tells the customer in plain words', async () => {
    const calls = installFetch(() => fakeResponse(409, { code: 'WORKBENCH_VERSION_CONFLICT' }));
    renderShell();
    openTool(copy.toolDecisions);
    fireEvent.click(screen.getByRole('button', { name: 'Decline publish' }));
    expect(await screen.findByText(copy.problems.WORKBENCH_VERSION_CONFLICT)).toBeInTheDocument();
    await waitFor(() => expect(calls.some((call) => call.method === 'GET' && call.path === '')).toBe(true));
  });

  it('explains that a fresh strong sign-in is needed', async () => {
    installFetch(() =>
      fakeResponse(403, {
        code: 'WORKBENCH_REQUEST_INVALID',
        detail: 'A fresh strong sign-in is required for this action.',
      })
    );
    renderShell();
    openTool(copy.toolDecisions);
    fireEvent.click(screen.getByRole('button', { name: 'Approve publish' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(copy.strongAuth);
  });

  it('reports a failed refresh without losing the current view', async () => {
    global.fetch = jest.fn(async () => fakeResponse(503, { code: 'WORKBENCH_UNAVAILABLE' })) as jest.Mock;
    renderShell();
    fireEvent.click(screen.getByRole('button', { name: copy.refresh }));
    expect(await screen.findByText(copy.refreshFailed)).toBeInTheDocument();
    expect(screen.getByText('One decision is waiting.')).toBeInTheDocument();
  });

  it('redeems a handoff link once, opens the tool it was issued for and clears the address', async () => {
    window.history.replaceState(null, '', `/relationships/${relationshipId}?handoff=h-abc`);
    const calls = installFetch(() =>
      fakeResponse(200, { schemaVersion: '1.0', purpose: 'APPROVAL', contextRef: 'decision-1' })
    );

    const { rerender } = render(
      <WorkbenchShell copy={copy} handoffToken="h-abc" initial={snapshotFixture()} relationshipId={relationshipId} />
    );

    expect(await screen.findByText('Publish the weekly update')).toBeInTheDocument();
    const rail = within(screen.getByRole('navigation', { name: copy.toolsLabel }));
    expect(rail.getByRole('button', { name: new RegExp(copy.toolDecisions) })).toHaveAttribute('aria-current', 'page');
    const consume = calls.filter((call) => call.path === '/handoffs/consume');
    expect(consume).toHaveLength(1);
    expect(consume[0].body).toEqual({ schemaVersion: '1.0', destinationRef: 'h-abc' });
    expect(consume[0].headers['Idempotency-Key']).toMatch(/[0-9a-f-]{36}/);
    expect(window.location.search).toBe('');
    rerender(
      <WorkbenchShell copy={copy} handoffToken="h-abc" initial={snapshotFixture()} relationshipId={relationshipId} />
    );
    expect(calls.filter((call) => call.path === '/handoffs/consume')).toHaveLength(1);
  });

  it('says in plain words that a handoff link is no longer valid and stays on the overview', async () => {
    installFetch(() => fakeResponse(404, { code: 'WORKBENCH_REQUEST_INVALID' }));
    render(
      <WorkbenchShell copy={copy} handoffToken="h-old" initial={snapshotFixture()} relationshipId={relationshipId} />
    );

    expect(await screen.findByText(copy.handoffInvalid)).toBeInTheDocument();
    const rail = within(screen.getByRole('navigation', { name: copy.toolsLabel }));
    expect(rail.getByRole('button', { name: copy.toolOverview })).toHaveAttribute('aria-current', 'page');
  });

  it('does not call the service when there is no handoff link', () => {
    const calls = installFetch(() => fakeResponse(200, {}));
    renderShell();
    expect(calls.filter((call) => call.path === '/handoffs/consume')).toHaveLength(0);
  });
});

describe('toolForPurpose', () => {
  it.each([
    ['APPROVAL', false, 'decisions'],
    ['EVIDENCE', false, 'evidence'],
    ['PAYMENT', false, 'wallet'],
    ['PAYMENT', true, 'overview'],
    ['WEB_WORKBENCH', false, 'overview'],
    ['SOMETHING_NEW', false, 'overview'],
  ])('opens %s (beneficiary %s) on %s', (purpose, beneficiary, expected) => {
    expect(toolForPurpose(purpose, beneficiary)).toBe(expected);
  });
});
