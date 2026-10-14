// Implements: Meta user-data deletion instructions requirement
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { LegalPage } from '@/components/public/LegalPage';
import { legalPages } from '@/config/public-pages';
import { publicMetadata } from '@/lib/public-seo';

export const metadata = publicMetadata(
  legalPages.dataDeletion.title,
  legalPages.dataDeletion.summary,
  legalPages.dataDeletion.path
);

export default function DataDeletionPage() {
  return <LegalPage {...legalPages.dataDeletion} />;
}
