import { redirect } from 'next/navigation';
import { AzureKeyVaultWriter } from '@/components/admin/AzureKeyVaultWriter';
import { keyVaultAdminEmail, keyVaultTarget } from '@/lib/key-vault-admin';
import { resolvePlatformAccess } from '@/lib/platform-access-server';
import { getServerAccessToken } from '@/lib/server-auth';

export default async function AzureKeyVaultPage() {
  const accessToken = await getServerAccessToken();
  // The platform Founder grant decides who may open this page; the Azure sign-in still restricts who may write.
  if (!accessToken || !(await resolvePlatformAccess(accessToken)).founder) redirect('/home');
  const target = keyVaultTarget();
  if (!target) {
    return (
      <section className="portal-page" aria-labelledby="key-vault-title">
        <header className="portal-heading">
          <p className="eyebrow">Azure administration</p>
          <h1 id="key-vault-title">Azure Key Vault unavailable</h1>
          <p>This deployment has no approved Key Vault target.</p>
        </header>
      </section>
    );
  }
  return (
    <section className="portal-page" aria-labelledby="key-vault-title">
      <header className="portal-heading">
        <p className="eyebrow">Azure administration</p>
        <h1 id="key-vault-title">Azure Key Vault</h1>
        <p>Values can be added or overwritten. Existing names and values are never displayed.</p>
      </header>
      <AzureKeyVaultWriter
        adminEmail={keyVaultAdminEmail()}
        clientId={target.clientId}
        environment={target.environment}
        tenantId={target.tenantId}
        vaultHost={new URL(target.vaultUrl).host}
      />
    </section>
  );
}
