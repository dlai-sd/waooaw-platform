import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AzureKeyVaultWriter } from './AzureKeyVaultWriter';

const initialize = jest.fn().mockResolvedValue(undefined);
const loginPopup = jest.fn().mockResolvedValue({ account: { username: 'yogesh.khandge@dlaisd.com' } });
const acquireTokenSilent = jest.fn().mockResolvedValue({ accessToken: 'azure-access-token' });

jest.mock('@azure/msal-browser', () => ({
  InteractionRequiredAuthError: class InteractionRequiredAuthError extends Error {},
  PublicClientApplication: jest.fn().mockImplementation(() => ({
    acquireTokenPopup: jest.fn(),
    acquireTokenSilent,
    getAllAccounts: jest.fn().mockReturnValue([]),
    initialize,
    loginPopup,
  })),
}));

beforeEach(() => {
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
  fireEvent.submit(screen.getByRole('button', { name: 'Save to Azure Key Vault' }).closest('form')!);

  expect(await screen.findByText(/Saved razorpay-test-key-id to codespace/)).toBeVisible();
  expect(screen.queryByText('sensitive-value')).not.toBeInTheDocument();
  expect(screen.getByLabelText('Secret value')).toHaveValue('');
  await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
    '/api/admin/azure-key-vault',
    expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer azure-access-token' }),
      method: 'POST',
    })
  ));
});
