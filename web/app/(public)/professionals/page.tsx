// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06 S01-S02
// Constitutional basis: C-009, C-048, C-049, C-059

import { Search } from 'lucide-react';
import { ProfessionalComparison } from '@/components/professionals/ProfessionalComparison';
import { discoverProfessionals, getProfessionalDisclosure } from '@/lib/api/professionals';

export default async function ProfessionalsPage({ searchParams }: { searchParams: Promise<{ outcome?: string }> }) {
	const outcome = (await searchParams).outcome?.trim() ?? '';
	let unavailable = false;
	const professionals = outcome.length >= 3
		? await discoverProfessionals(outcome)
				.then((results) => Promise.all(results.map((result) => getProfessionalDisclosure(result.professionalType))))
				.catch(() => { unavailable = true; return []; })
		: [];

	return (
		<main className="catalog-shell">
			<header className="catalog-header"><p className="brand">WAOOAW PROFESSIONALS</p><h1>What outcome does your business need?</h1><p>Describe the result. Suitability is based on lawful capability, never a preferred-customer score.</p></header>
			<form className="outcome-search" method="get">
				<label htmlFor="outcome">Business outcome</label>
				<div><input id="outcome" name="outcome" defaultValue={outcome} minLength={3} maxLength={500} placeholder="For example, bring more local customers to my clinic" required /><button type="submit" aria-label="Find suitable professionals"><Search aria-hidden="true" size={20} /> Find professionals</button></div>
			</form>
			{unavailable ? <p className="catalog-unavailable" role="status">Professional discovery is temporarily unavailable. No suitability claim can be made.</p> : outcome.length >= 3 ? <ProfessionalComparison professionals={professionals} /> : <p className="catalog-prompt">Start with a concrete business result to compare suitable professionals and inspect every limitation before trial.</p>}
		</main>
	);
}