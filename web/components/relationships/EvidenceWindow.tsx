'use client';

import { useState } from 'react';
import type { RelationshipEvidencePageV1 } from '@/lib/api/generated/models/RelationshipEvidencePageV1';
import { RelationshipEvidenceExportOutcomeV1FromJSON } from '@/lib/api/generated/models/RelationshipEvidenceExportOutcomeV1';

export function EvidenceWindow({ relationshipId, evidence }: {
  relationshipId: string;
  evidence: RelationshipEvidencePageV1;
}) {
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function requestExport() {
    setStatus('Preparing evidenced export');
    const response = await fetch(`/api/relationships/${encodeURIComponent(relationshipId)}/evidence-export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ purpose: 'Customer relationship evidence review' }),
    });
    if (!response.ok) {
      setStatus('Export unresolved');
      return;
    }
    const result = RelationshipEvidenceExportOutcomeV1FromJSON(await response.json());
    setDownloadUrl(result.downloadUrl ?? null);
    setStatus(result.status === 'COMPLETED' && result.downloadUrl ? 'Export ready' : 'Export unresolved');
  }

  return (
    <section className="timeline evidence-window" aria-labelledby="evidence-window-title">
      <p className="section-label">Evidence</p>
      <div className="evidence-window-heading">
        <h2 id="evidence-window-title">Customer evidence window</h2>
        <button type="button" onClick={requestExport}>Export evidence</button>
      </div>
      <p className="currency-state">Participant observation unresolved</p>
      {status && <p role="status">{status}</p>}
      {downloadUrl && <a href={downloadUrl}>Download evidence export</a>}
      {evidence.items.length === 0 ? <p className="empty-meaning">No customer-visible evidence is recorded yet.</p> : (
        <ol>{evidence.items.map((item) => <li key={item.evidenceId}><span>{item.subject}</span><strong>{item.state.toLowerCase()}</strong></li>)}</ol>
      )}
    </section>
  );
}