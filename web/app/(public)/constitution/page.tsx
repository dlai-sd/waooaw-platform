// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Information Architecture
// Constitutional basis: C-059 (Implementation Traceability)
import { InformationPage } from '@/components/public/InformationPage'; import { publicPages } from '@/config/public-pages';
import { publicMetadata } from '@/lib/public-seo';
export const metadata = publicMetadata(publicPages.constitution.title, publicPages.constitution.summary, publicPages.constitution.path);
export default function ConstitutionPage() { return <InformationPage {...publicPages.constitution} />; }