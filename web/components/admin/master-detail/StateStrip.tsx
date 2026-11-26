// Implements: work-contracts/WC-172-safe-to-charge-real-customers.md (Demo defect repairs: master-detail admin pages)
// Constitutional basis: C-023, C-059

const steps = [
  { state: 'DRAFT', label: 'Draft' },
  { state: 'SIMULATED', label: 'Simulated' },
  { state: 'SUBMITTED', label: 'Submitted' },
  { state: 'AUTHORIZED', label: 'Authorized' },
  { state: 'EFFECTIVE', label: 'In force' },
] as const;

const endNotes: Record<string, string> = {
  DISCARDED: 'This version was discarded and can no longer be used.',
  SUPERSEDED: 'A newer version replaced this one.',
};

/** Shows where a pricing version is on its way to being in force, so the next step is never a guess. */
export function StateStrip({ state, finalLabel }: { state: string; finalLabel?: string }) {
  const reached = steps.findIndex((step) => step.state === state);
  return (
    <div className="state-strip-wrap">
      <ol aria-label="Progress" className="state-strip">
        {steps.map((step, index) => (
          <li
            aria-current={index === reached ? 'step' : undefined}
            className={index < reached ? 'done' : index === reached ? 'current' : undefined}
            key={step.state}
          >
            {step.state === 'EFFECTIVE' && finalLabel ? finalLabel : step.label}
          </li>
        ))}
      </ol>
      {endNotes[state] ? <p className="workbench-hint">{endNotes[state]}</p> : null}
    </div>
  );
}
