import 'server-only';

import type { JWT } from 'next-auth/jwt';
import type { IdentityProviderLinkOperationV1 } from '@/lib/api/generated/models/IdentityProviderLinkOperationV1';
import { createIdentityApi } from '@/lib/api/identity';
import { revokeAllSessions } from '@/lib/web-session-store';

export async function enforceAuthorityChangeRevocation(
  operation: IdentityProviderLinkOperationV1,
  token: JWT,
  accessToken: string,
  idempotencyKey: string
): Promise<boolean> {
  if (operation.state !== 'COMPLETED') return false;
  await revokeAllSessions(token, `IDENTITY_${operation.command}`);
  await createIdentityApi(accessToken).createIdentitySessionRevocation(
    {
      idempotencyKey,
      identitySessionRevocationRequestV1: {
        schemaVersion: '1.0',
        scope: 'ALL',
        reason: 'SECURITY_EVENT',
        correlationId: operation.operationReference,
      },
    },
    { cache: 'no-store' }
  );
  return true;
}
