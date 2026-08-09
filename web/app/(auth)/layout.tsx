// Implements: architecture/reference/ux/hybrid-application-shell.md §Web and Mobile Authentication Layout
// Constitutional basis: C-059 (Implementation Traceability)

import type { ReactNode } from 'react';
import { AppShell } from '@/components/shell/AppShell';
export default function AuthLayout({ children }: { children: ReactNode }) { return <AppShell variant="auth">{children}</AppShell>; }