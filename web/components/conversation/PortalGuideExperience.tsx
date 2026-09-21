'use client';

// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R005
// Constitutional basis: C-026 (Tenant Isolation), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { ArrowUp, LoaderCircle } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { PortalInteractionMessageV1 } from '@/lib/api/generated/models/PortalInteractionMessageV1';
import { PortalInteractionSubmissionV1FromJSON } from '@/lib/api/generated/models/PortalInteractionSubmissionV1';
import { PortalInteractionTimelinePageV1FromJSON } from '@/lib/api/generated/models/PortalInteractionTimelinePageV1';
import type { PortalInteractionSurfaceV1 } from '@/lib/api/generated/models/PortalInteractionSurfaceV1';

const draftKey = 'waooaw:conversation:portal:draft';

export function PortalGuideExperience({
  currentSurface,
  locale = 'en-IN',
}: {
  currentSurface: PortalInteractionSurfaceV1;
  locale?: string;
}) {
  const [messages, setMessages] = useState<PortalInteractionMessageV1[]>([]);
  const [cursor, setCursor] = useState('');
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setDraft(localStorage.getItem(draftKey) ?? '');
    fetch('/api/interactions/portal?limit=40', { cache: 'no-store' })
      .then(async (response) => {
        if (!response.ok) throw new Error('Guide conversation is unavailable.');
        const page = PortalInteractionTimelinePageV1FromJSON(await response.json());
        setMessages(page.items);
        setCursor(page.authoritativeCursor);
      })
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : 'Guide conversation is unavailable.')
      )
      .finally(() => setLoading(false));
  }, []);

  function updateDraft(value: string) {
    setDraft(value);
    if (value) localStorage.setItem(draftKey, value);
    else localStorage.removeItem(draftKey);
  }

  async function send() {
    const text = draft.trim();
    if (!text || sending) return;
    setSending(true);
    setError('');
    try {
      const response = await fetch('/api/interactions/portal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idempotencyKey: crypto.randomUUID(),
          clientMessageId: crypto.randomUUID(),
          text,
          locale,
          currentSurface,
          expectedCursor: cursor || undefined,
        }),
      });
      if (!response.ok) throw new Error('The Guide response is unresolved. Refresh before retrying.');
      const submission = PortalInteractionSubmissionV1FromJSON(await response.json());
      setMessages((current) => [...current, submission.customerMessage, submission.guideMessage]);
      setCursor(submission.authoritativeCursor);
      updateDraft('');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The Guide response is unresolved.');
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="portal-guide" aria-labelledby="portal-guide-title">
      <header>
        <h2 id="portal-guide-title">WAOOAW Guide</h2>
        <span>{currentSurface.replaceAll('_', ' ').toLowerCase()}</span>
      </header>
      <p className="scope-disclosure">
        Navigation and explanations only. The Guide cannot act as an employed professional.
      </p>
      <div className="portal-guide-timeline" aria-busy={loading} aria-live="polite">
        {loading ? (
          <p>
            <LoaderCircle aria-hidden="true" className="spin" size={18} /> Loading Guide…
          </p>
        ) : null}
        {!loading && messages.length === 0 ? (
          <p>Ask where to find agents, alerts, billing or account settings.</p>
        ) : null}
        {messages.map((message) => (
          <article className={`guide-message guide-message-${message.actor.toLowerCase()}`} key={message.messageId}>
            <strong>{message.actor === 'CUSTOMER' ? 'You' : 'WAOOAW Guide'}</strong>
            {message.content.map((block, index) => (
              <p key={`${message.messageId}-${index}`}>{block.text}</p>
            ))}
            {message.capabilities.map((capability) => (
              <Link
                className="secondary-link"
                href={capability.destination}
                key={`${message.messageId}-${capability.destination}`}
              >
                {capability.label}
              </Link>
            ))}
          </article>
        ))}
      </div>
      {error ? (
        <p className="conversation-error" role="alert">
          {error}
        </p>
      ) : null}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void send();
        }}
      >
        <label htmlFor="portal-guide-draft">Ask the Guide</label>
        <div className="portal-guide-composer">
          <textarea
            id="portal-guide-draft"
            maxLength={4000}
            onChange={(event) => updateDraft(event.target.value)}
            placeholder="Where can I review my agents?"
            rows={3}
            value={draft}
          />
          <button
            aria-label="Send"
            className="send-command"
            disabled={!draft.trim() || sending}
            title="Send"
            type="submit"
          >
            {sending ? (
              <LoaderCircle aria-hidden="true" className="spin" size={18} />
            ) : (
              <ArrowUp aria-hidden="true" size={18} />
            )}
          </button>
        </div>
      </form>
    </section>
  );
}
