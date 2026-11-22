'use client';

// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R009, WC149-R010
// Constitutional basis: C-026, C-059, C-063

import { useId, useState } from 'react';
import { PricingMessage, type PricingNotice } from '@/components/admin/pricing/usePricingCommand';
import { connectionCall } from '@/lib/provider-connections-call';
import {
  formatWhen,
  maximumPostLength,
  problemText,
  type ProviderConnection,
  type PublishResult,
} from '@/lib/provider-connections-client';

type Props = {
  connection: ProviderConnection;
  onNeedsRepair: () => void;
};

export function PublishForm({ connection, onNeedsRepair }: Props) {
  const ids = useId();
  const [text, setText] = useState('');
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<PricingNotice | null>(null);
  const [published, setPublished] = useState<PublishResult | null>(null);

  function edit(next: string) {
    setText(next);
    setApproved(false);
  }

  async function publish() {
    setBusy(true);
    setMessage(null);
    setPublished(null);
    const result = await connectionCall<PublishResult>('POST', `/${connection.id}/publish`, {
      message: text,
      approved: true,
      approvalNote: 'Approved by the customer on the Connections screen.',
    });
    if (result.ok) {
      setPublished(result.data);
      setText('');
      setApproved(false);
    } else {
      setMessage({ kind: 'error', text: problemText(result.problem) });
      if (result.problem.code === 'CONNECTION_NEEDS_REPAIR') onNeedsRepair();
    }
    setBusy(false);
  }

  const canPublish = approved && text.trim().length > 0 && text.length <= maximumPostLength && !busy;
  return (
    <fieldset className="workbench-form providers-value connections-publish">
      <legend>Publish an approved post</legend>
      <label>
        Post message
        <textarea
          aria-describedby={`${ids}-hint ${ids}-count`}
          disabled={busy}
          maxLength={maximumPostLength}
          onChange={(event) => edit(event.target.value)}
          value={text}
        />
      </label>
      <p className="connections-counter" id={`${ids}-count`}>
        {text.length} / {maximumPostLength}
      </p>
      <p className="workbench-hint" id={`${ids}-hint`}>
        Nothing is published until you tick the approval box. Changing the text clears your approval, so the post that
        goes out is exactly the one you approved.
      </p>
      <label className="providers-acknowledge">
        <input
          checked={approved}
          disabled={busy}
          onChange={(event) => setApproved(event.target.checked)}
          type="checkbox"
        />
        I approve this exact post to be published to my Facebook Page
      </label>
      <div className="workbench-actions">
        <button className="primary-command" disabled={!canPublish} onClick={() => void publish()} type="button">
          {busy ? 'Publishing...' : 'Publish post'}
        </button>
      </div>
      <output aria-live="polite" className="providers-test-result">
        {published ? (
          <p data-outcome="PASSED">
            <strong>Published.</strong> Facebook post id {published.providerPostId}
            {published.publishedAt ? ` at ${formatWhen(published.publishedAt)}` : ''}.
          </p>
        ) : null}
      </output>
      <PricingMessage message={message} />
    </fieldset>
  );
}
