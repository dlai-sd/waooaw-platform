import { AuthDialog } from '@/components/auth/AuthDialog';
import { RegisterView } from '@/components/auth/RegisterView';

export default function RegisterDialogPage() {
  return <AuthDialog><RegisterView /></AuthDialog>;
}