import { InteractionRequiredAuthError } from '@azure/msal-browser';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AzureKeyVaultWriter } from './AzureKeyVaultWriter';

const initialize = jest.fn().mockResolvedValue(undefined);
const loginPopup = jest.fn().mockResolvedValue({ account: { username: 'yogesh.khandge@dlaisd.com' } });
const acquireTokenSilent = jest.fn().mockResolvedValue({ accessToken: 'azure-access-token' });
const acquireTokenPopup = jest.fn().mockResolvedValue({ accessToken: 'azure-popup-token' });
const getAllAccounts = jest.fn().mockReturnValue([]);

function submitSecretForm() {
  const form = screen.getByRole('button', { name: 'Save to Azure Key Vault' }).closest('form');
  if (!form) throw new Error('Expected the save command to belong to a form.');
  fireEvent.submit(form);
}

jest.mock('@azure/msal-browser', () => ({
  InteractionRequiredAuthError: class InteractionRequiredAuthError extends Error {},
  PublicClientApplication: jest.fn().mockImplementation(() => ({
    acquireTokenPopup,
    acquireTokenSilent,
    getAllAccounts,
    initialize,
    loginPopup,
  })),
}));

beforeEach(() => {
  jest.clearAllMocks();
  getAllAccounts.mockReturnValue([]);
  loginPopup.mockResolvedValue({ account: { username: 'yogesh.khandge@dlaisd.com' } });
  acquireTokenSilent.mockResolvedValue({ accessToken: 'azure-access-token' });
  acquireTokenPopup.mockResolvedValue({ accessToken: 'azure-popup-token' });
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ environment: 'codespace', name: 'razorpay-test-key-id', status: 'SAVED' }),
  });
});

test('uses Azure authorization, clears the value, and never displays it after saving', async () => {
  render(
    <AzureKeyVaultWriter
      adminEmail="yogesh.khandge@dlaisd.com"
      clientId="client-id"
      environment="codespace"
      tenantId="tenant-id"
      vaultHost="waooaw-dev-kv.vault.azure.net"
    />
  );
  fireEvent.change(screen.getByLabelText('Secret name'), { target: { value: 'razorpay-test-key-id' } });
  fireEvent.change(screen.getByLabelText('Secret value'), { target: { value: 'sensitive-value' } });
  const form = screen.getByRole('button', { name: 'Save to Azure Key Vault' }).closest('form');
  if (!form) throw new Error('Expected the save command to belong to a form.');
  fireEvent.submit(form);

  expect(await screen.findByText(/Saved razorpay-test-key-id to codespace/)).toBeVisible();
  expect(screen.queryByText('sensitive-value')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Secret value')).toHaveValue('');
  await waitFor(() =>
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/admin/azure-key-vault',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer azure-access-token' }),
        method: 'POST',
      })
    )
  );
});

test('reuses the matching Azure account without another login', async () => {
  getAllAccounts.mockReturnValue([{ username: 'YOGESH.KHANDGE@DLAISD.COM' }]);
  render(
    <AzureKeyVaultWriter
      adminEmail="yogesh.khandge@dlaisd.com"
      clientId="client-id"
      environment="demo"
      tenantId="tenant-id"
      vaultHost="waooaw-demo-kv.vault.azure.net"
    />
  );
  fireEvent.change(screen.getByLabelText('Secret name'), { target: { value: 'existing-secret' } });
  fireEvent.change(screen.getByLabelText('Secret value'), { target: { value: 'replacement' } });
  submitSecretForm();

  expect(await screen.findByText(/Saved existing-secret to demo/)).toBeVisible();
  expect(loginPopup).not.toHaveBeenCalled();
  expect(acquireTokenSilent).toHaveBeenCalledWith(
    expect.objectContaining({ account: expect.objectContaining({ username: 'YOGESH.KHANDGE@DLAISD.COM' }) })
  );
});

test('falls back to interactive token acquisition when Azure requires interaction', async () => {
  acquireTokenSilent.mockRejectedValue(new InteractionRequiredAuthError('interaction required'));
  render(
    <AzureKeyVaultWriter
      adminEmail="yogesh.khandge@dlaisd.com"
      clientId="client-id"
      environment="codespace"
      tenantId="tenant-id"
      vaultHost="waooaw-dev-kv.vault.azure.net"
    />
  );
  fireEvent.change(screen.getByLabelText('Secret name'), { target: { value: 'popup-secret' } });
  fireEvent.change(screen.getByLabelText('Secret value'), { target: { value: 'value' } });
  submitSecretForm();

  await waitFor(() => expect(acquireTokenPopup).toHaveBeenCalledTimes(1));
  expect(global.fetch).toHaveBeenCalledWith(
    '/api/admin/azure-key-vault',
    expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer azure-popup-token' }) })
  );
});

test('reports the server title when the write is rejected', async () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: false,
    json: async () => ({ title: 'The secret name is not permitted.' }),
  });
  render(
    <AzureKeyVaultWriter
      adminEmail="yogesh.khandge@dlaisd.com"
      clientId="client-id"
      environment="codespace"
      tenantId="tenant-id"
      vaultHost="waooaw-dev-kv.vault.azure.net"
    />
  );
  fireEvent.change(screen.getByLabelText('Secret name'), { target: { value: 'blocked-secret' } });
  fireEvent.change(screen.getByLabelText('Secret value'), { target: { value: 'value' } });
  submitSecretForm();

  const message = await screen.findByText('The secret name is not permitted.');
  expect(message).toHaveClass('error-copy');
});

test('uses a safe fallback when Azure returns a malformed error response', async () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: false,
    json: async () => {
      throw new Error('invalid json');
    },
  });
  render(
    <AzureKeyVaultWriter
      adminEmail="yogesh.khandge@dlaisd.com"
      clientId="client-id"
      environment="codespace"
      tenantId="tenant-id"
      vaultHost="waooaw-dev-kv.vault.azure.net"
    />
  );
  fireEvent.change(screen.getByLabelText('Secret name'), { target: { value: 'malformed-response' } });
  fireEvent.change(screen.getByLabelText('Secret value'), { target: { value: 'value' } });
  submitSecretForm();

  expect(await screen.findByText('Azure Key Vault could not save the secret.')).toHaveClass('error-copy');
});
