// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Approved Landing Composition
// Constitutional basis: C-059 (Implementation Traceability)

import { CookiePreferencesTrigger } from './CookiePreferencesTrigger';
import { siteConfig } from '@/config/site';

export function PublicFooter() {
  return <footer className="public-footer"><div className="footer-brand"><strong>WAOOAW</strong><p>Governed digital professionals. Visible scope. Reviewable work. Control remains yours.</p></div>{siteConfig.footerGroups.map((group) => <nav aria-label={group.label} key={group.label}><strong>{group.label}</strong>{group.links.map((link) => <a href={link.href} key={link.href}>{link.label}</a>)}{group.label === 'Legal' ? <CookiePreferencesTrigger /> : null}</nav>)}<div className="footer-contact"><strong>Support</strong><a href={`mailto:${siteConfig.contactEmail}`}>{siteConfig.contactEmail}</a><small>{siteConfig.company}</small></div></footer>;
}