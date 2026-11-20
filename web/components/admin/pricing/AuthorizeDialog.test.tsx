// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import type { ComponentProps } from 'react';
import { fakeResponse, simulationFixture, versionFixture, versionId } from '@/lib/pricing-admin-test-data';
import { AuthorizeDialog } from './AuthorizeDialog';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const originalFetch = global.fetch;
const version = versionFixture({ state: 'SUBMITTED', kind: 'PACKAGE', subjectKey: 'package:dma|v3|STARTER' });
const calm = { ...simulationFixture, warnings: [] };

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
});

function open(props: Partial<ComponentProps<typeof AuthorizeDialog>> = {}) {
  const onClose = jest.fn();
  const onAuthorized = jest.fn();
  render(
    <AuthorizeDialog
      isFounder
      onAuthorized={onAuthorized}
      onClose={onClose}
      simulation={calm}
      version={version}
      {...props}
    />
  );
  return { onClose, onAuthorized };
}

test('an administrator sees why authorize is unavailable', () => {
  open({ isFounder: false });

  expect(screen.getByText('Only the Founder can authorize a pricing version.')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Authorize' })).toBeDisabled();
  expect(screen.getByLabelText('Effective from (UTC, optional)')).toBeDisabled();
});

test('the dialog takes focus, closes on Escape and names itself', () => {
  const { onClose } = open();

  expect(screen.getByRole('dialog', { name: /Authorize package package:dma\|v3\|STARTER/ })).toHaveAttribute(
    'aria-modal',
    'true'
  );
  expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus();
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'a' });
  expect(onClose).toHaveBeenCalledTimes(1);
});

test('the Founder authorizes with the version tag and an optional UTC start', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, { ...version, state: 'AUTHORIZED' }));
  const { onAuthorized } = open();

  fireEvent.change(screen.getByLabelText('Effective from (UTC, optional)'), { target: { value: '2027-01-01T10:00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Authorize' }));

  await waitFor(() => expect(onAuthorized).toHaveBeenCalledWith(expect.objectContaining({ state: 'AUTHORIZED' })));
  const [url, init] = jest.mocked(global.fetch).mock.calls[0];
  expect(url).toBe(`/api/admin/pricing/drafts/${versionId}/authorize`);
  expect(JSON.parse(String(init?.body))).toEqual({
    schemaVersion: '1.0',
    expectedVersion: '2:SUBMITTED:abcdef0123456789',
    secondConfirmation: false,
    effectiveFrom: '2027-01-01T10:00:00.000Z',
  });
});

test('a guarded change needs the second confirmation before authorize enables', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(200, version));
  open({ simulation: simulationFixture });

  const authorize = screen.getByRole('button', { name: 'Authorize' });
  expect(authorize).toBeDisabled();
  fireEvent.click(screen.getByLabelText('I confirm this large change a second time'));
  expect(authorize).toBeEnabled();
  fireEvent.click(authorize);

  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  expect(JSON.parse(String(jest.mocked(global.fetch).mock.calls[0][1]?.body)).secondConfirmation).toBe(true);
});

test('an unavailable component is listed as a sale gate and does not stop authorization', () => {
  open({
    simulation: {
      ...calm,
      warnings: [
        { code: 'PACKAGE_COMPONENT_NOT_AVAILABLE', componentId: 'ads', message: 'Ad boost is not available.' },
      ],
    },
  });

  expect(screen.getByRole('list', { name: 'Gates before sale' })).toHaveTextContent(
    'Cannot go on sale yet: Ad boost is not available.'
  );
  expect(screen.getByRole('button', { name: 'Authorize' })).toBeEnabled();
});

test('authorizing before simulating prompts for the simulation', () => {
  open({ simulation: null });
  expect(screen.getByText(/Run the simulation first/)).toBeInTheDocument();
});

test('a missing step-up offers the multi-factor sign-in', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(403, { code: 'PRICING_STEP_UP_REQUIRED' }));
  open();

  fireEvent.click(screen.getByRole('button', { name: 'Authorize' }));

  const stepUp = await screen.findByRole('button', { name: 'Confirm with multi-factor sign-in' });
  expect(screen.getByRole('alert')).toHaveTextContent('multi-factor');
  fireEvent.click(stepUp);
  expect(signIn).toHaveBeenCalledWith(
    'keycloak',
    expect.objectContaining({ waooawIntent: 'LOGIN' }),
    expect.objectContaining({ prompt: 'login', max_age: '0' })
  );
});

test('another failure is shown without the step-up offer', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(409, { code: 'PRICING_ILLEGAL_TRANSITION' }));
  const { onAuthorized } = open();

  fireEvent.click(screen.getByRole('button', { name: 'Authorize' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('not in a state');
  expect(screen.queryByRole('button', { name: 'Confirm with multi-factor sign-in' })).toBeNull();
  expect(onAuthorized).not.toHaveBeenCalled();
});
