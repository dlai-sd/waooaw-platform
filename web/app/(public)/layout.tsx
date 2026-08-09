// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import type { ReactNode } from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { getRequestI18n } from '@/lib/i18n-server';

export default function PublicLayout({ children }: { children: ReactNode }) {
	const { messages } = getRequestI18n();
	return <AppShell messages={messages} variant="public">{children}</AppShell>;
}