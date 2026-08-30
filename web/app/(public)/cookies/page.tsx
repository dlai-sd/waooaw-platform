// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Content Rules
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { LegalPage } from '@/components/public/LegalPage'; import { legalPages } from '@/config/public-pages';
import { publicMetadata } from '@/lib/public-seo';
export const metadata = publicMetadata(legalPages.cookies.title, legalPages.cookies.summary, legalPages.cookies.path);
export default function CookiesPage() { return <LegalPage {...legalPages.cookies} />; }