import { Check, FlaskConical, Scale, ShieldCheck } from 'lucide-react';
import type { ProfessionalDisclosure } from '@/lib/api/professionals';

export function ProfessionalComparison({ professionals }: { professionals: ProfessionalDisclosure[] }) {
  if (professionals.length === 0) {
    return <p className="catalog-empty">No suitable professional was found for that outcome. Refine the business result, not a preferred customer profile.</p>;
  }

  return (
    <div className="comparison-grid">
      {professionals.map((professional) => (
        <article className="professional-comparison" key={professional.professionalType}>
          <header>
            <div><p className="section-label">Suitable professional</p><h2>{professional.displayName}</h2></div>
            <span className="fit-mark"><Check aria-hidden="true" size={16} /> Eligible</span>
          </header>
          <p className="fit-reason">{professional.eligibility.explanation}</p>
          <ul className="suitability-list">{professional.suitability.map((reason) => <li key={reason}>{reason}</li>)}</ul>

          <div className="disclosure-band">
            <section><h3><FlaskConical aria-hidden="true" size={18} /> 14-day evaluation</h3><p>{professional.skills.filter((skill) => skill.applicableInTrial).length} skills can be demonstrated using local inference, with no paid APIs and no external actions.</p></section>
            <section><h3><ShieldCheck aria-hidden="true" size={18} /> Rights and evidence</h3><p>{professional.evidencePosture}</p><ul>{professional.customerRights.map((right) => <li key={right}>{right}</li>)}</ul></section>
            <section><h3><Scale aria-hidden="true" size={18} /> Limits and authority</h3><ul>{professional.limitations.map((limit) => <li key={limit}>{limit}</li>)}</ul><p><strong>Authority needed:</strong> {professional.authorityNeeds.join(' · ')}</p></section>
          </div>

          <details>
            <summary>Inspect all {professional.skills.length} skills</summary>
            <ul className="skill-disclosure">{professional.skills.map((skill) => <li key={skill.skillId}><span>{skill.displayName}</span><small>{skill.applicableInTrial ? 'Trial demonstration available' : skill.activationCondition ?? 'Available after activation'}</small></li>)}</ul>
          </details>
          <footer><span>Indicative price</span><strong>{new Intl.NumberFormat('en-IN', { style: 'currency', currency: professional.indicativePrice.currency }).format(professional.indicativePrice.amountInrPaise / 100)} / {professional.indicativePrice.cadence.toLowerCase()}</strong><small>{professional.indicativePrice.qualification}</small></footer>
          <a className="primary-command" href={`/login?professional=${encodeURIComponent(professional.professionalType)}`}>Interview this professional</a>
        </article>
      ))}
    </div>
  );
}