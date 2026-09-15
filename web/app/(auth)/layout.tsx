// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-059 (Implementation Traceability)

import type { ReactNode } from 'react';
import { getServerSession } from 'next-auth';
import { AppShell } from '@/components/shell/AppShell';
import { ProtectedAppShell } from '@/components/shell/ProtectedAppShell';
import { authOptions } from '@/lib/auth';
import { getRequestI18n } from '@/lib/i18n-server';
export default async function AuthLayout({ children }: { children: ReactNode }) {
	const session = await getServerSession(authOptions);
	const { locale, messages } = await getRequestI18n();
	if (session?.authenticated) return <ProtectedAppShell locale={locale} messages={messages} variant="customer">{children}</ProtectedAppShell>;
	return <AppShell messages={messages} variant="auth">{children}</AppShell>;
}