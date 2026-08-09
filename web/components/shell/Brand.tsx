// Implements: architecture/reference/ux/hybrid-visual-system-contract.md §Global Chrome
// Constitutional basis: C-059 (Implementation Traceability)

import Image from 'next/image';

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <a className="brand-link" href="/" aria-label="WAOOAW home">
      <Image alt="" height={32} priority src="/waooaw-platform-logo.png" width={compact ? 34 : 152} />
      {compact ? <span className="visually-hidden">WAOOAW</span> : null}
    </a>
  );
}