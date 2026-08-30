// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Professional Catalogue Boundary
// Constitutional basis: C-002, C-059

import type { Metadata } from 'next';
import { PublicCatalogue } from '@/components/public/PublicCatalogue';
import { listPublicProfessionals } from '@/config/professionals';
import { publicMetadata } from '@/lib/public-seo';

export const metadata: Metadata = publicMetadata('Digital professionals | WAOOAW', 'Explore governed digital professionals, their outcomes, and their limits.', '/professionals');

export default function ProfessionalsPage() {
	return (
		<div className="catalog-shell">
			<header className="catalog-header"><p className="brand">WAOOAW PROFESSIONALS</p><h1>Choose a professional by the work you need.</h1><p>Each publication shows approved outcomes and honest limits. It does not claim live availability or suitability for your business.</p></header>
			<PublicCatalogue professionals={listPublicProfessionals()} />
		</div>
	);
}