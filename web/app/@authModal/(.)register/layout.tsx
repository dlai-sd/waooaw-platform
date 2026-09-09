import type { ReactNode } from 'react';
import { AuthDialog } from '@/components/auth/AuthDialog';

export default function RegisterDialogLayout({ children }: { children: ReactNode }) {
  return <AuthDialog>{children}</AuthDialog>;
}