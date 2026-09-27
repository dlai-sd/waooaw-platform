// Implements: architecture/reference/ux/wc-105-authentication-flow-defect-remediation-plan.md AUTH-UI-05
// Constitutional basis: C-059 (Implementation Traceability)

import type { ReactNode } from 'react';
import { AuthDialog } from '@/components/auth/AuthDialog';
import { AppShell } from '@/components/shell/AppShell';
import { getRequestI18n } from '@/lib/i18n-server';
export default async function AuthLayout({ children }: { children: ReactNode }) {
  const { messages } = await getRequestI18n();
  return (
    <AppShell messages={messages} variant="auth">
      <AuthDialog variant="entry">{children}</AuthDialog>
    </AppShell>
  );
}
