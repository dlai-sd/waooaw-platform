import { LoginView } from '@/components/auth/LoginView';

export default function LoginDialogPage({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> }) {
  return <LoginView searchParams={searchParams} />;
}