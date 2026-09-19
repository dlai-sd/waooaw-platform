// Implements: work-contracts/WC-093-public-auth-experience-finalization.md WC093-A06
// Constitutional basis: C-059 (Implementation Traceability)

import Image from 'next/image';

export function AuthBrand({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="auth-brand">
      <span className="auth-brand-logo">
        <Image alt="WAOOAW" height={104} priority src="/waooaw-platform-logo.png" width={104} />
      </span>
      <div>
        <h1 id="auth-dialog-title">{title}</h1>
        <p>{subtitle}</p>
      </div>
    </header>
  );
}
