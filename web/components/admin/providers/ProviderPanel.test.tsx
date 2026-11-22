// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R003, WC148-R004, WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { fakeResponse } from '@/lib/pricing-admin-test-data';
import type { CredentialVersion, ProviderSummary } from '@/lib/provider-admin-client';
import { ProviderPanel } from './ProviderPanel';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const secret = 'sk-live-0123456789-keep-me-out-of-the-page';
const providerId = '7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11';
const provider: ProviderSummary = {
  id: providerId,
  providerName: 'sarvam',
  displayName: 'Sarvam',
  category: 'PLATFORM_LLM',
  agentTypeId: null,
  authMethod: 'API_KEY',
  hasTestEndpoint: true,
  active: true,
  credential: {
    status: 'ACTIVE',
    activeVersionNo: 2,
    activatedAt: '2027-01-02T03:04:05Z',
    lastTestOutcome: 'PASSED',
  },
};
const versions: CredentialVersion[] = [
  {
    versionId: 'b1',
    versionNo: 2,
    status: 'ACTIVE',
    createdAt: '2027-01-02T03:04:05Z',
    activatedAt: '2027-01-02T03:04:06Z',
    testOutcome: 'PASSED',
  },
  {
    versionId: 'a1',
    versionNo: 1,
    status: 'SUPERSEDED',
    createdAt: '2026-12-01T00:00:00Z',
    activatedAt: '2026-12-01T00:00:01Z',
    testOutcome: null,
  },
];

type Route = (body: Record<string, unknown>) => Response;
const originalFetch = global.fetch;

function serve(routes: Record<string, Route | Response>) {
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const key = `${init?.method ?? 'GET'} ${String(input).replace('/api/admin/providers', '')}`;
    const route = routes[key];
    if (!route) return fakeResponse(404, { code: 'PROVIDER_NOT_FOUND' });
    return typeof route === 'function' ? route(init?.body ? JSON.parse(String(init.body)) : {}) : route;
  }) as typeof fetch;
}

const history = fakeResponse(200, versions);
const base = `/${providerId}/credentials`;

function open(onChanged = jest.fn()) {
  render(<ProviderPanel focusOnMount={false} onChanged={onChanged} provider={provider} />);
  return { onChanged };
}

function valueInput() {
  return screen.getByLabelText('API key or secret value') as HTMLInputElement;
}

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
});

test('the value field is a password field that never autofills and the copy says it can never be read back', async () => {
  serve({ [`GET ${base}`]: history });
  open();

  const input = valueInput();
  expect(input).toHaveAttribute('type', 'password');
  expect(input).toHaveAttribute('autocomplete', 'new-password');
  expect(input).toHaveAccessibleDescription(/can never be read back/);
  expect(screen.getByRole('group', { name: 'Enter a new value' })).toBeInTheDocument();
  await screen.findByRole('table', { name: 'Sarvam version history' });
});

test('Confirm and save stays disabled until the latest test of the current value passes', async () => {
  serve({
    [`GET ${base}`]: history,
    [`POST ${base}/test`]: fakeResponse(200, {
      outcome: 'PASSED',
      detail: 'Provider accepted the key.',
      httpStatus: 200,
    }),
  });
  open();
  const save = screen.getByRole('button', { name: 'Confirm and save' });
  const test = screen.getByRole('button', { name: 'Test' });

  expect(save).toBeDisabled();
  expect(test).toBeDisabled();
  fireEvent.change(valueInput(), { target: { value: secret } });
  expect(test).toBeEnabled();
  expect(save).toBeDisabled();

  fireEvent.click(test);

  await screen.findByText(/Provider accepted the key\./);
  expect(save).toBeEnabled();
  expect(test).toHaveFocus();

  fireEvent.change(valueInput(), { target: { value: `${secret}x` } });
  expect(save).toBeDisabled();
  expect(screen.queryByText(/Provider accepted the key\./)).not.toBeInTheDocument();
});

test('a passing test then save sends the value once, clears it, and leaves no value in the page', async () => {
  const saved = jest.fn((body: Record<string, unknown>) => {
    void body;
    return fakeResponse(201, {
      versionId: 'c1',
      versionNo: 3,
      status: 'ACTIVE',
    });
  });
  serve({
    [`GET ${base}`]: history,
    [`POST ${base}/test`]: fakeResponse(200, {
      outcome: 'PASSED',
      detail: 'ok',
    }),
    [`POST ${base}`]: saved,
  });
  const { onChanged } = open();
  fireEvent.change(valueInput(), { target: { value: secret } });
  fireEvent.click(screen.getByRole('button', { name: 'Test' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirm and save' })).toBeEnabled());

  fireEvent.click(screen.getByRole('button', { name: 'Confirm and save' }));

  await screen.findByText(/Saved as version 3 and active now/);
  expect(saved).toHaveBeenCalledWith({ value: secret });
  expect(valueInput().value).toBe('');
  expect(valueInput()).toHaveFocus();
  expect(document.body.innerHTML).not.toContain(secret);
  expect(screen.getByRole('button', { name: 'Confirm and save' })).toBeDisabled();
  expect(onChanged).toHaveBeenCalledTimes(1);
});

test('a failed test clears the value and keeps Confirm and save disabled', async () => {
  serve({
    [`GET ${base}`]: history,
    [`POST ${base}/test`]: fakeResponse(200, {
      outcome: 'FAILED',
      detail: 'The provider rejected the key.',
      httpStatus: 401,
    }),
  });
  open();
  fireEvent.change(valueInput(), { target: { value: secret } });

  fireEvent.click(screen.getByRole('button', { name: 'Test' }));

  await screen.findByText(/The provider rejected the key\./);
  expect(screen.getByText(/HTTP 401/)).toBeInTheDocument();
  expect(valueInput().value).toBe('');
  expect(screen.getByRole('button', { name: 'Confirm and save' })).toBeDisabled();
  expect(document.body.innerHTML).not.toContain(secret);
});

test('a value that cannot be tested saves only after the explicit acknowledgement', async () => {
  const saved = jest.fn(() => fakeResponse(201, { versionId: 'c1', versionNo: 3, status: 'ACTIVE' }));
  serve({
    [`GET ${base}`]: history,
    [`POST ${base}/test`]: fakeResponse(200, {
      outcome: 'NOT_TESTABLE',
      detail: 'This provider has no test endpoint.',
    }),
    [`POST ${base}`]: saved,
  });
  open();
  fireEvent.change(valueInput(), { target: { value: secret } });
  fireEvent.click(screen.getByRole('button', { name: 'Test' }));
  const acknowledge = await screen.findByRole('checkbox', {
    name: /Save without a test/,
  });
  const save = screen.getByRole('button', { name: 'Confirm and save' });

  expect(save).toBeDisabled();
  fireEvent.click(acknowledge);
  expect(save).toBeEnabled();
  fireEvent.click(save);

  await screen.findByText(/Saved as version 3/);
  expect(saved).toHaveBeenCalledWith({
    value: secret,
    acknowledgeUntested: true,
  });
});

test('a rejected save explains why, clears the value and offers the step-up sign-in when it is required', async () => {
  serve({
    [`GET ${base}`]: history,
    [`POST ${base}/test`]: fakeResponse(200, {
      outcome: 'PASSED',
      detail: 'ok',
    }),
    [`POST ${base}`]: fakeResponse(403, { code: 'PROVIDER_STEP_UP_REQUIRED' }),
  });
  open();
  fireEvent.change(valueInput(), { target: { value: secret } });
  fireEvent.click(screen.getByRole('button', { name: 'Test' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Confirm and save' })).toBeEnabled());

  fireEvent.click(screen.getByRole('button', { name: 'Confirm and save' }));

  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent('Confirm your identity again with multi-factor sign-in');
  expect(valueInput().value).toBe('');
  fireEvent.click(screen.getByRole('button', { name: 'Confirm with multi-factor sign-in' }));
  expect(signIn).toHaveBeenCalledWith(
    'keycloak',
    expect.objectContaining({ waooawIntent: 'LOGIN' }),
    expect.objectContaining({ prompt: 'login', max_age: '0', acr_values: '2' })
  );
});

test('a test that cannot run clears the value and shows the vault problem', async () => {
  serve({
    [`GET ${base}`]: history,
    [`POST ${base}/test`]: fakeResponse(503, {
      code: 'PROVIDER_VAULT_UNAVAILABLE',
    }),
  });
  open();
  fireEvent.change(valueInput(), { target: { value: secret } });

  fireEvent.click(screen.getByRole('button', { name: 'Test' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('The secret store is unavailable. Nothing was saved.');
  expect(valueInput().value).toBe('');
  expect(valueInput()).toHaveFocus();
});

test('the history lists versions and offers roll back only on superseded versions', async () => {
  serve({ [`GET ${base}`]: history });
  open();

  const table = await screen.findByRole('table', {
    name: 'Sarvam version history',
  });

  expect(
    within(table)
      .getAllByRole('columnheader')
      .map((cell) => cell.textContent)
  ).toEqual(['Version', 'Status', 'Saved', 'Activated', 'Last test', 'Action']);
  expect(within(table).getAllByRole('button')).toHaveLength(1);
  expect(
    within(table).getByRole('button', {
      name: 'Roll back to this version (version 1)',
    })
  ).toBeInTheDocument();
  expect(within(table).getAllByText('2027-01-02 03:04 UTC')).toHaveLength(2);
  expect(within(table).getByText('Not tested')).toBeInTheDocument();
});

test('roll back asks for confirmation, can be cancelled with Escape, and returns focus', async () => {
  const activate = jest.fn(() => fakeResponse(200, { versionId: 'a1', versionNo: 1, status: 'ACTIVE' }));
  serve({ [`GET ${base}`]: history, [`POST ${base}/a1/activate`]: activate });
  open();
  const opener = await screen.findByRole('button', {
    name: /Roll back to this version/,
  });
  opener.focus();

  fireEvent.click(opener);

  const dialog = screen.getByRole('dialog', {
    name: 'Roll back Sarvam to version 1?',
  });
  expect(dialog).toHaveAttribute('aria-modal', 'true');
  expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus();
  expect(activate).not.toHaveBeenCalled();
  fireEvent.keyDown(dialog, { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
  expect(activate).not.toHaveBeenCalled();
});

test('confirming a roll back re-activates that version and refreshes', async () => {
  const activate = jest.fn(() => fakeResponse(200, { versionId: 'a1', versionNo: 1, status: 'ACTIVE' }));
  serve({ [`GET ${base}`]: history, [`POST ${base}/a1/activate`]: activate });
  const { onChanged } = open();
  fireEvent.click(await screen.findByRole('button', { name: /Roll back to this version/ }));

  fireEvent.click(screen.getByRole('button', { name: 'Confirm roll back' }));

  await screen.findByText(/Rolled back\. Version 1 is active now/);
  expect(activate).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(onChanged).toHaveBeenCalledTimes(1);
});

test('a roll back that needs a fresh sign-in shows the step-up command inside the dialog', async () => {
  serve({
    [`GET ${base}`]: history,
    [`POST ${base}/a1/activate`]: fakeResponse(403, {
      code: 'PROVIDER_STEP_UP_REQUIRED',
    }),
  });
  open();
  fireEvent.click(await screen.findByRole('button', { name: /Roll back to this version/ }));

  fireEvent.click(screen.getByRole('button', { name: 'Confirm roll back' }));

  const dialog = screen.getByRole('dialog');
  expect(
    await within(dialog).findByRole('button', {
      name: 'Confirm with multi-factor sign-in',
    })
  ).toBeInTheDocument();
  expect(within(dialog).getByRole('alert')).toHaveTextContent('multi-factor');
});

test('history loading, empty and error states are announced and the error can be retried', async () => {
  let attempts = 0;
  global.fetch = jest.fn(async () => {
    attempts += 1;
    if (attempts === 1) return fakeResponse(503, { code: 'PROVIDER_VAULT_UNAVAILABLE' });
    return fakeResponse(200, []);
  }) as typeof fetch;
  open();

  expect(screen.getByText('Loading version history...').tagName).toBe('OUTPUT');
  expect(await screen.findByRole('alert')).toHaveTextContent('Version history could not be loaded.');

  fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

  expect(await screen.findByText('No value has been saved for this provider yet.')).toBeInTheDocument();
});

test('the panel heading takes focus when the Founder just selected the provider', async () => {
  serve({ [`GET ${base}`]: history });
  render(<ProviderPanel focusOnMount onChanged={jest.fn()} provider={provider} />);

  expect(screen.getByRole('heading', { level: 2, name: 'Sarvam' })).toHaveFocus();
  await screen.findByRole('table');
});
