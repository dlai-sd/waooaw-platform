// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063, C-088

import type { Diff } from '@/lib/pricing-admin-types';

export function VersionDiff({ diff }: { diff?: Diff }) {
  if (!diff || diff.changes.length === 0) {
    return <p className="workbench-hint">No difference from the effective version.</p>;
  }
  return (
    <table aria-label="Changes against the effective version">
      <thead>
        <tr>
          <th scope="col">Field</th>
          <th scope="col">Effective now</th>
          <th scope="col">This draft</th>
        </tr>
      </thead>
      <tbody>
        {diff.changes.map((change) => (
          <tr key={change.path}>
            <th scope="row">{change.path}</th>
            <td>{change.before ?? 'not set'}</td>
            <td>{change.after ?? 'removed'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
