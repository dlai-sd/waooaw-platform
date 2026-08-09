// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import type { ReactNode } from 'react';
import { AppShell } from '@/components/shell/AppShell';

export default function PublicLayout({ children }: { children: ReactNode }) { return <AppShell variant="public">{children}</AppShell>; }