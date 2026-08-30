// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Content Rules
// Constitutional basis: C-059 (Implementation Traceability)
import { LegalPage } from '@/components/public/LegalPage'; import { legalPages } from '@/config/public-pages';
import { publicMetadata } from '@/lib/public-seo';
export const metadata = publicMetadata(legalPages.grievance.title, legalPages.grievance.summary, legalPages.grievance.path);
export default function GrievancePage() { return <LegalPage {...legalPages.grievance} />; }