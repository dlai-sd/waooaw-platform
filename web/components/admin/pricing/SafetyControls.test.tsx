// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { fakeResponse, versionFixture, versionId } from '@/lib/pricing-admin-test-data';
import { SafetyControls } from './SafetyControls';

const originalFetch = global.fetch;
const packages = [versionFixture({ kind: 'PACKAGE', subjectKey: 'package:dma|v3|STARTER', versionNo: 4 })];
const grants = [
  versionFixture({ kind: 'GRANT', subjectKey: 'grant:TRIAL|dma|v3', versionNo: 1 }),
  versionFixture({ kind: 'GRANT', subjectKey: 'grant:TRIAL|dma|v3', versionNo: 2 }),
];

afterEach(() => {
  global.fetch = originalFetch;
});

function form(name: string) {
  return within(screen.getByRole('form', { name }));
}

test('each control says it takes effect now and is available without the Founder role', () => {
  render(<SafetyControls grants={grants} packages={packages} />);

  expect(screen.getAllByText(/takes effect now/)).toHaveLength(3);
  expect(screen.getByRole('region', { name: 'Safety controls' })).toBeInTheDocument();
  expect(screen.getAllByRole('option', { name: 'grant:TRIAL|dma|v3' })).toHaveLength(1);
});

test('lowering a ceiling needs every field and then reports the immediate effect', async () => {
  global.fetch = jest
    .fn()
    .mockResolvedValue(fakeResponse(200, { direction: 'SAFETY', state: 'EFFECTIVE', founderNotified: true }));
  render(<SafetyControls grants={grants} packages={packages} />);
  const ceiling = form('Lower a ceiling');

  fireEvent.click(ceiling.getByRole('button', { name: 'Lower ceiling now' }));
  expect(ceiling.getByRole('alert')).toHaveTextContent('Choose a scope and give its reference.');

  fireEvent.change(ceiling.getByLabelText('Ceiling scope'), { target: { value: 'ENVIRONMENT_CEILING' } });
  fireEvent.change(ceiling.getByLabelText('Scope reference'), { target: { value: ' demo ' } });
  fireEvent.change(ceiling.getByLabelText('New maximum (INR)'), { target: { value: '2.555' } });
  fireEvent.click(ceiling.getByRole('button', { name: 'Lower ceiling now' }));
  expect(ceiling.getByRole('alert')).toHaveTextContent('at most two decimals');

  fireEvent.change(ceiling.getByLabelText('New maximum (INR)'), { target: { value: '250' } });
  fireEvent.click(ceiling.getByRole('button', { name: 'Lower ceiling now' }));
  expect(ceiling.getByRole('alert')).toHaveTextContent('Give a reason.');
  expect(global.fetch).not.toHaveBeenCalled();

  fireEvent.change(ceiling.getByLabelText('Reason for lowering'), { target: { value: 'Spend spike' } });
  fireEvent.click(ceiling.getByRole('button', { name: 'Lower ceiling now' }));

  await waitFor(() =>
    expect(ceiling.getByRole('status')).toHaveTextContent('It took effect now. The Founder was notified.')
  );
  const [url, init] = jest.mocked(global.fetch).mock.calls[0];
  expect(url).toBe('/api/admin/pricing/safety/lower-ceiling');
  expect(JSON.parse(String(init?.body))).toEqual({
    schemaVersion: '1.0',
    scope: 'ENVIRONMENT_CEILING',
    ref: 'demo',
    newMaximumPaise: 25000,
    reason: 'Spend spike',
  });
});

test('closing a package names the package and keeps existing customers in the message', async () => {
  global.fetch = jest
    .fn()
    .mockResolvedValue(fakeResponse(200, { direction: 'SAFETY', state: 'SUPERSEDED', founderNotified: false }));
  render(<SafetyControls grants={grants} packages={packages} />);
  const closing = form('Close a package to new customers');

  fireEvent.click(closing.getByRole('button', { name: 'Close to new customers now' }));
  expect(closing.getByRole('alert')).toHaveTextContent('Choose the package to close.');
  fireEvent.change(closing.getByLabelText('Package'), { target: { value: versionId } });
  fireEvent.click(closing.getByRole('button', { name: 'Close to new customers now' }));
  expect(closing.getByRole('alert')).toHaveTextContent('Give a reason.');
  fireEvent.change(closing.getByLabelText('Reason for closing'), { target: { value: 'Provider price rise' } });
  fireEvent.click(closing.getByRole('button', { name: 'Close to new customers now' }));

  await waitFor(() =>
    expect(closing.getByRole('status')).toHaveTextContent('Existing customers keep it. It took effect now.')
  );
  expect(closing.getByRole('status')).not.toHaveTextContent('Founder was notified');
  expect(JSON.parse(String(jest.mocked(global.fetch).mock.calls[0][1]?.body))).toMatchObject({ packageId: versionId });
});

test('disabling a grant sends the subject key and shows a refusal in words', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(403, { code: 'PRICING_FORBIDDEN' }));
  render(<SafetyControls grants={grants} packages={packages} />);
  const disabling = form('Disable a grant');

  fireEvent.click(disabling.getByRole('button', { name: 'Disable grant now' }));
  expect(disabling.getByRole('alert')).toHaveTextContent('Choose the grant to disable.');
  fireEvent.change(disabling.getByLabelText('Grant'), { target: { value: 'grant:TRIAL|dma|v3' } });
  fireEvent.click(disabling.getByRole('button', { name: 'Disable grant now' }));
  expect(disabling.getByRole('alert')).toHaveTextContent('Give a reason.');
  fireEvent.change(disabling.getByLabelText('Reason for disabling'), { target: { value: 'Abuse' } });
  fireEvent.click(disabling.getByRole('button', { name: 'Disable grant now' }));

  await waitFor(() => expect(disabling.getByRole('alert')).toHaveTextContent('Your role may not do this.'));
  expect(JSON.parse(String(jest.mocked(global.fetch).mock.calls[0][1]?.body))).toMatchObject({
    subjectKey: 'grant:TRIAL|dma|v3',
  });
});
