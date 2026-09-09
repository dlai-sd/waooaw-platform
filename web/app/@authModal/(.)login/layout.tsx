import type { ReactNode } from 'react';
import { AuthDialog } from '@/components/auth/AuthDialog';

export default function LoginDialogLayout({ children }: { children: ReactNode }) {
  return <AuthDialog>{children}</AuthDialog>;
}