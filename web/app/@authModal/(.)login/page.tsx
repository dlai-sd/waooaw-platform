import { AuthDialog } from '@/components/auth/AuthDialog';
import { LoginView } from '@/components/auth/LoginView';

export default function LoginDialogPage({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> }) {
  return <AuthDialog><LoginView searchParams={searchParams} /></AuthDialog>;
}