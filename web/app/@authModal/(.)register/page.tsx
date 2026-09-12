import { RegisterView } from '@/components/auth/RegisterView';

export default function RegisterDialogPage({ searchParams }: { searchParams?: Promise<{ returnTo?: string | string[] }> }) {
  return <RegisterView searchParams={searchParams} />;
}