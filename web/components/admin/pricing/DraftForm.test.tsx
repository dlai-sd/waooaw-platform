// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { fakeResponse, versionFixture, versionId } from '@/lib/pricing-admin-test-data';
import { formSpecs } from '@/lib/pricing-forms';
import { DraftForm } from './DraftForm';

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
});

function type(label: string | RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

test('a budget draft is created with rupees converted to paise and the owner subject key', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, versionFixture({ kind: 'BUDGET' })));
  const onSaved = jest.fn();
  render(<DraftForm draft={null} onSaved={onSaved} spec={formSpecs.BUDGET} />);

  type('Budget scope', 'SIMULATION');
  type('Scope reference', 'demo');
  type('Maximum (INR)', '50');
  type('Reason for the change (optional)', 'Raise cap');
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  await waitFor(() => expect(onSaved).toHaveBeenCalled());
  const [url, init] = jest.mocked(global.fetch).mock.calls[0];
  expect(url).toBe('/api/admin/pricing/drafts');
  expect(JSON.parse(String(init?.body))).toEqual({
    schemaVersion: '1.0',
    kind: 'BUDGET',
    subjectKey: 'budget:SIMULATION|demo',
    body: { scope: 'SIMULATION', ref: 'demo', maximumPaise: 5000 },
    reason: 'Raise cap',
  });
  expect(screen.getByRole('status')).toHaveTextContent('Draft created.');
});

test('invalid fields are named, described and announced and nothing is sent', () => {
  global.fetch = jest.fn();
  render(<DraftForm draft={null} onSaved={jest.fn()} spec={formSpecs.RATE} />);

  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  const field = screen.getByLabelText('Thread identifier');
  expect(field).toHaveAttribute('aria-invalid', 'true');
  expect(field).toHaveAccessibleDescription('Thread identifier is required.');
  expect(screen.getByRole('alert')).toHaveTextContent('Some fields need attention');
  expect(global.fetch).not.toHaveBeenCalled();
});

test('an existing draft is edited in place with its version tag', async () => {
  const draft = versionFixture({
    kind: 'COUPON',
    body: {
      code: 'WELCOME',
      agentType: 'dma',
      agentVersion: 'v3',
      percent: 10,
      capPaise: 10000,
      expiresAt: '2027-01-01T00:00:00.000Z',
      reason: 'Goodwill',
      maxRedemptions: 5,
    },
  });
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, draft));
  render(<DraftForm draft={draft} onSaved={jest.fn()} spec={formSpecs.COUPON} />);

  expect(screen.getByLabelText('Coupon code (capital letters and digits)')).toHaveValue('WELCOME');
  expect(screen.getByLabelText('Expires at (UTC)')).toHaveValue('2027-01-01T00:00');
  type('Discount cap (INR)', '120');
  fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  const [url, init] = jest.mocked(global.fetch).mock.calls[0];
  expect(url).toBe(`/api/admin/pricing/drafts/${versionId}`);
  expect(init?.method).toBe('PUT');
  expect(JSON.parse(String(init?.body))).toMatchObject({
    expectedVersion: '2:DRAFT:abcdef0123456789',
    body: { capPaise: 12000 },
  });
});

test('a version that is no longer editable starts a new draft from its values', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, versionFixture()));
  const effective = versionFixture({
    state: 'EFFECTIVE',
    body: {
      threadId: 'llm',
      provider: 'p',
      unit: 'tok',
      rawCostPaise: 3,
      fxBufferPct: 1,
      opsOverheadPct: 1,
      riskPremiumPct: 1,
    },
  });
  render(<DraftForm draft={effective} onSaved={jest.fn()} spec={formSpecs.RATE} />);

  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  expect(jest.mocked(global.fetch).mock.calls[0][1]?.method).toBe('POST');
});

test('an owner rejection is shown with its violations', async () => {
  global.fetch = jest.fn().mockResolvedValue(
    fakeResponse(422, {
      code: 'PRICING_DRAFT_INVALID',
      violations: [{ code: 'X', path: 'body.rawCostPaise', message: 'Must be positive.' }],
    })
  );
  const onSaved = jest.fn();
  render(
    <DraftForm
      draft={null}
      onSaved={onSaved}
      seedBody={{
        threadId: 'llm',
        provider: 'p',
        unit: 'tok',
        rawCostPaise: 0,
        fxBufferPct: 1,
        opsOverheadPct: 1,
        riskPremiumPct: 1,
      }}
      spec={formSpecs.RATE}
    />
  );

  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('body.rawCostPaise: Must be positive.');
  expect(onSaved).not.toHaveBeenCalled();
});
