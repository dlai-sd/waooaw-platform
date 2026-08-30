// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Hero Autonomy Handoff Console
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability)

import { Check, CircleDot, FileCheck2, Play } from 'lucide-react';

const states = [
  { title: 'Trial started', detail: 'Explore the professional with no commitment.', state: 'Ready', Icon: Play },
  { title: 'Business understood', detail: 'Your goals and working context are captured.', state: 'Understood', Icon: CircleDot },
  { title: 'Scope approved', detail: 'You confirm what the professional may and may not do.', state: 'Approved', Icon: FileCheck2 },
  { title: 'Working autonomously', detail: 'Productive work has started.', state: 'Active', Icon: Check },
] as const;

export function AutonomyHandoffConsole() {
  return <section className="handoff-console" aria-labelledby="handoff-title"><p className="illustrative-label">Illustrative journey</p><h2 id="handoff-title">From trial to autonomous productivity — in minutes</h2><ol>{states.map(({ detail, Icon, state, title }, index) => <li key={title} style={{ '--handoff-order': index } as React.CSSProperties}><Icon aria-hidden="true" size={18} /><span><strong>{title}</strong><small>{detail}</small></span><b>{state}</b></li>)}</ol></section>;
}