// Implements: work-contracts/WC-172-safe-to-charge-real-customers.md (Demo defect repairs: master-detail admin pages)
// Constitutional basis: C-023, C-059

import Link from 'next/link';

export type Crumb = { label: string; href?: string; onSelect?: () => void };

/** Where the person is in a list -> detail -> part flow; every earlier step is a way back. */
export function Breadcrumb({ trail }: { trail: Crumb[] }) {
  return (
    <nav aria-label="Where you are" className="master-detail-breadcrumb">
      <ol>
        {trail.map((crumb, index) => {
          const last = index === trail.length - 1;
          return (
            <li aria-current={last ? 'page' : undefined} key={`${crumb.label}:${index}`}>
              {last ? (
                crumb.label
              ) : crumb.href ? (
                <Link href={crumb.href}>{crumb.label}</Link>
              ) : (
                <button className="text-command" onClick={crumb.onSelect} type="button">
                  {crumb.label}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
