'use client';

// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §UX-SHELL-05
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability)

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <html lang="en"><body><main className="system-page"><section className="state-view"><h1>Something went wrong</h1><p>The outcome is unknown. Try the request again.</p><button className="primary-command" type="button" onClick={reset}>Try again</button></section></main></body></html>;
}