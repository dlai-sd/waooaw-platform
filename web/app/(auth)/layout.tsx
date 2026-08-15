// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-059 (Implementation Traceability)

import type { ReactNode } from 'react';
import { getServerSession } from 'next-auth';
import { AccountSwitchCommand, SignOutCommand } from '@/components/auth/SignOutCommand';
import { AppShell } from '@/components/shell/AppShell';
import { authOptions } from '@/lib/auth';
import { getRequestI18n } from '@/lib/i18n-server';
export default async function AuthLayout({ children }: { children: ReactNode }) {
	const session = await getServerSession(authOptions);
	const { messages } = await getRequestI18n();
	const headerStatus = session?.authenticated ? <><AccountSwitchCommand label="Switch account" /><SignOutCommand label="Sign out" /></> : undefined;
	return <AppShell headerStatus={headerStatus} messages={messages} variant="auth">{children}</AppShell>;
}