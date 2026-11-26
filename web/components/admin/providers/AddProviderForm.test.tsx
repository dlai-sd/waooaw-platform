// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Constitutional basis: C-023, C-059, C-063, C-083

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { fakeResponse } from '@/lib/pricing-admin-test-data';
import { savePendingStepUp } from '@/lib/step-up-resume';
import { AddProviderForm } from './AddProviderForm';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
  window.sessionStorage.clear();
});

function openForm(onCreated = jest.fn()) {
  render(<AddProviderForm onCreated={onCreated} />);
  const toggle = screen.getByRole('button', { name: 'Add provider' });
  fireEvent.click(toggle);
  return { onCreated, toggle };
}

test('the form is collapsed until asked for, then takes focus, and Cancel returns focus to the toggle', () => {
  render(<AddProviderForm onCreated={jest.fn()} />);
  const toggle = screen.getByRole('button', { name: 'Add provider' });

  expect(toggle).toHaveAttribute('aria-expanded', 'false');
  expect(screen.queryByLabelText('Provider name')).not.toBeInTheDocument();
  fireEvent.click(toggle);
  expect(toggle).toHaveAttribute('aria-expanded', 'true');
  expect(screen.getByLabelText('Provider name')).toHaveFocus();
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(screen.queryByLabelText('Provider name')).not.toBeInTheDocument();
  expect(toggle).toHaveFocus();
});

test('invalid fields are named next to the field and nothing is sent', () => {
  global.fetch = jest.fn();
  openForm();
  fireEvent.change(screen.getByLabelText('Provider name'), {
    target: { value: 'A' },
  });
  fireEvent.change(screen.getByLabelText(/Test address/), {
    target: { value: 'http://insecure.example' },
  });
  fireEvent.change(screen.getByLabelText('How the value is sent in the test'), {
    target: { value: 'HEADER' },
  });

  fireEvent.click(screen.getByRole('button', { name: 'Create provider' }));

  expect(screen.getByLabelText('Provider name')).toHaveAttribute('aria-invalid', 'true');
  expect(screen.getByLabelText('Provider name')).toHaveAccessibleDescription(/2 to 48 lowercase letters/);
  expect(screen.getByText('Enter a display name of at least 2 characters.')).toBeInTheDocument();
  expect(screen.getByText('The test address must start with https://.')).toBeInTheDocument();
  expect(screen.getByText('Enter the header name the provider expects.')).toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('Fix the highlighted fields');
  expect(global.fetch).not.toHaveBeenCalled();
});

test('a valid provider with a test endpoint is created with the chosen scheme', async () => {
  const created = { id: 'p9', providerName: 'acme-search' };
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, created));
  const { onCreated } = openForm();
  fireEvent.change(screen.getByLabelText('Provider name'), {
    target: { value: 'Acme-Search' },
  });
  fireEvent.change(screen.getByLabelText('Display name'), {
    target: { value: ' Acme Search ' },
  });
  fireEvent.change(screen.getByLabelText('Category'), {
    target: { value: 'AGENT_API' },
  });
  fireEvent.change(screen.getByLabelText('Agent type (optional)'), {
    target: { value: 'dma' },
  });
  fireEvent.change(screen.getByLabelText(/Test address/), {
    target: { value: 'https://api.acme.example/me' },
  });
  fireEvent.change(screen.getByLabelText('How the value is sent in the test'), {
    target: { value: 'HEADER' },
  });
  fireEvent.change(screen.getByLabelText('Header name'), {
    target: { value: 'X-Acme-Key' },
  });

  fireEvent.click(screen.getByRole('button', { name: 'Create provider' }));

  await waitFor(() => expect(onCreated).toHaveBeenCalledWith(created));
  const [url, init] = jest.mocked(global.fetch).mock.calls[0];
  expect(url).toBe('/api/admin/providers');
  expect(JSON.parse(String(init?.body))).toEqual({
    providerName: 'acme-search',
    displayName: 'Acme Search',
    category: 'AGENT_API',
    agentTypeId: 'dma',
    testUrl: 'https://api.acme.example/me',
    testAuthScheme: 'HEADER',
    testAuthHeader: 'X-Acme-Key',
  });
  expect(screen.queryByLabelText('Provider name')).not.toBeInTheDocument();
});

test('a provider without a test endpoint sends only the registry fields', async () => {
  global.fetch = jest.fn().mockResolvedValue(fakeResponse(201, { id: 'p9' }));
  openForm();
  fireEvent.change(screen.getByLabelText('Provider name'), {
    target: { value: 'openai-eu' },
  });
  fireEvent.change(screen.getByLabelText('Display name'), {
    target: { value: 'OpenAI EU' },
  });

  fireEvent.click(screen.getByRole('button', { name: 'Create provider' }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  expect(JSON.parse(String(jest.mocked(global.fetch).mock.calls[0][1]?.body))).toEqual({
    providerName: 'openai-eu',
    displayName: 'OpenAI EU',
    category: 'PLATFORM_LLM',
  });
});

test('a conflict keeps the form open and explains it; a step-up requirement offers the sign-in', async () => {
  global.fetch = jest
    .fn()
    .mockResolvedValueOnce(fakeResponse(409, { code: 'PROVIDER_CONFLICT' }))
    .mockResolvedValueOnce(fakeResponse(403, { code: 'PROVIDER_STEP_UP_REQUIRED' }));
  const { onCreated } = openForm();
  fireEvent.change(screen.getByLabelText('Provider name'), {
    target: { value: 'openai' },
  });
  fireEvent.change(screen.getByLabelText('Display name'), {
    target: { value: 'OpenAI' },
  });

  fireEvent.click(screen.getByRole('button', { name: 'Create provider' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('already exists');
  fireEvent.click(screen.getByRole('button', { name: 'Create provider' }));
  fireEvent.click(
    await screen.findByRole('button', {
      name: 'Confirm with multi-factor sign-in',
    })
  );

  expect(signIn).toHaveBeenCalledTimes(1);
  expect(onCreated).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Provider name')).toHaveValue('openai');
  const remembered = JSON.parse(window.sessionStorage.getItem('waooaw.step-up.providers.add') ?? '{}');
  expect(remembered.payload).toMatchObject({ providerName: 'openai', displayName: 'OpenAI', category: 'PLATFORM_LLM' });
});

test('after the step-up the form reopens with its fields and waits for Create provider', () => {
  savePendingStepUp('providers.add', {
    providerName: 'acme-search',
    displayName: 'Acme Search',
    category: 'AGENT_API',
    agentTypeId: 'dma',
    testUrl: 'https://api.acme.example/ping',
    scheme: 'HEADER',
    authHeader: 'X-Acme-Key',
  });
  global.fetch = jest.fn();
  render(<AddProviderForm onCreated={jest.fn()} />);

  expect(screen.getByLabelText('Provider name')).toHaveValue('acme-search');
  expect(screen.getByLabelText('Display name')).toHaveValue('Acme Search');
  expect(screen.getByLabelText('Category')).toHaveValue('AGENT_API');
  expect(screen.getByLabelText('Agent type (optional)')).toHaveValue('dma');
  expect(screen.getByLabelText('Header name')).toHaveValue('X-Acme-Key');
  expect(screen.getByText('You are signed in with extra security. Press Create provider to continue.')).toBeVisible();
  expect(global.fetch).not.toHaveBeenCalled();
});
