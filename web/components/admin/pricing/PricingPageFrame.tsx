// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import Link from 'next/link';
import type { ReactNode } from 'react';

export const pricingSections = [
  { href: '/admin/pricing', label: 'Overview' },
  { href: '/admin/pricing/rates', label: 'Rates' },
  { href: '/admin/pricing/packages', label: 'Packages' },
  { href: '/admin/pricing/policy', label: 'Policy' },
  { href: '/admin/pricing/grants', label: 'Grants' },
  { href: '/admin/pricing/budgets', label: 'Budgets' },
  { href: '/admin/pricing/coupons', label: 'Coupons' },
  { href: '/admin/pricing/dashboard', label: 'Funding and margin' },
] as const;

type Props = { current: string; title: string; intro: string; children: ReactNode };

export function PricingPageFrame({ current, title, intro, children }: Props) {
  return (
    <section aria-labelledby="pricing-title" className="portal-page">
      <header className="portal-heading">
        <p className="eyebrow">Pricing administration</p>
        <h1 id="pricing-title">{title}</h1>
        <p>{intro}</p>
        <nav aria-label="Pricing sections">
          <ul className="workbench-plain-list">
            {pricingSections.map((section) => (
              <li key={section.href}>
                <Link
                  aria-current={section.href === current ? 'page' : undefined}
                  className="secondary-link"
                  href={section.href}
                >
                  {section.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      {children}
    </section>
  );
}
