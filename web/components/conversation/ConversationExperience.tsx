'use client';

// Implements: architecture/reference/ux/wc-034-implementation-decomposition.md §F3 Conversation Core
// Constitutional basis: C-001 (Human Override), C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)

import {
  Ban,
  Check,
  CircleAlert,
  CircleCheck,
  Clock3,
  LoaderCircle,
  RotateCcw,
  Send,
  Square,
  WifiOff,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import type { ConversationMessageV1 } from '@/lib/api/generated/models/ConversationMessageV1';
import type { ConversationStreamEventV1 } from '@/lib/api/generated/models/ConversationStreamEventV1';
import { ConversationSubmissionV1FromJSON } from '@/lib/api/generated/models/ConversationSubmissionV1';
import {
  ConversationTimelinePageV1FromJSON,
  type ConversationTimelinePageV1,
} from '@/lib/api/generated/models/ConversationTimelinePageV1';
import type { GovernedConversationCardV1 } from '@/lib/api/generated/models/GovernedConversationCardV1';

interface QueuedContribution {
  clientMessageId: string;
  idempotencyKey: string;
  text: string;
}

interface ConversationExperienceProps {
  relationshipId: string;
  locale?: string;
}

type ConnectionState = 'connecting' | 'live' | 'offline' | 'reconnecting' | 'stopped';

function storageKey(relationshipId: string, kind: 'draft' | 'outbox') {
  return `waooaw:conversation:${relationshipId}:${kind}`;
}

function retryKey(relationshipId: string, messageId: string) {
  return `waooaw:conversation:${relationshipId}:retry:${messageId}`;
}

function cancellationKey(relationshipId: string, executionId: string) {
  return `waooaw:conversation:${relationshipId}:cancel:${executionId}`;
}

function streamCursorKey(relationshipId: string) {
  return `waooaw:conversation:${relationshipId}:stream-cursor`;
}

function mergeMessages(current: ConversationMessageV1[], incoming: ConversationMessageV1[]) {
  const canonical = new Map(current.map((message) => [message.messageId, message]));
  incoming.forEach((message) => canonical.set(message.messageId, message));
  return [...canonical.values()].sort((left, right) => left.sequence - right.sequence);
}

async function readProblem(response: Response): Promise<string> {
  const body = await response.json().catch(() => undefined) as { title?: unknown } | undefined;
  return typeof body?.title === 'string' ? body.title : 'The conversation outcome is unknown. Reconnect before retrying.';
}

async function consumeEventStream(
  response: Response,
  onEvent: (event: ConversationStreamEventV1) => Promise<void>,
) {
  if (!response.body) throw new Error('Conversation stream has no readable body.');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replaceAll('\r\n', '\n');
    let boundary = buffer.indexOf('\n\n');
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const data = block
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
        .join('\n');
      if (data) await onEvent(JSON.parse(data) as ConversationStreamEventV1);
      boundary = buffer.indexOf('\n\n');
    }
    if (done) return;
  }
}

function Card({ card, canRetry, onRetry }: {
  card: GovernedConversationCardV1;
  canRetry: boolean;
  onRetry: () => void;
}) {
  const detail = card.cardType === 'ACTION'
    ? card.goal
    : card.cardType === 'PLAN'
      ? `${card.goal} · ${card.progressState}`
      : card.cardType === 'DELIVERABLE'
        ? `${card.title} · ${card.deliverableState}`
        : `${card.decisionState} · ${card.authorityImpact}`;

  return (
    <article className={`conversation-card conversation-card-${card.cardType.toLowerCase()}`} aria-label={`${card.cardType.toLowerCase()} card`}>
      <div className="conversation-card-heading">
        <span>{card.cardType}</span>
        <strong>{card.state}</strong>
      </div>
      <p>{detail}</p>
      <dl>
        <div><dt>Owner</dt><dd>{card.owner}</dd></div>
        <div><dt>Effect</dt><dd>{card.effect}</dd></div>
      </dl>
      {card.commands.length > 0 ? (
        <div className="card-commands" aria-label="Card commands">
          {card.commands.map((command) => (
            (() => {
              const supported = card.cardType !== 'PLAN' && command.commandId === 'RETRY_MESSAGE' && canRetry;
              const enabled = command.availability === 'AVAILABLE' && supported;
              return (
                <button
                  disabled={!enabled}
                  key={command.commandId}
                  onClick={enabled ? onRetry : undefined}
                  title={!enabled ? command.unavailableReason ?? 'This command is not available in the current release.' : undefined}
                  type="button"
                >
                  {command.availability === 'COMPLETED' ? <Check aria-hidden="true" size={16} /> : null}
                  {command.label}
                </button>
              );
            })()
          ))}
        </div>
      ) : null}
    </article>
  );
}

function MessageStatus({ message }: { message: ConversationMessageV1 }) {
  const delivery = message.deliveryState === 'ACCEPTED'
    ? { icon: CircleCheck, label: 'Accepted by WAOOAW' }
    : message.deliveryState === 'LOCAL_ONLY'
      ? { icon: Clock3, label: 'Unsent on this device' }
      : { icon: CircleAlert, label: message.deliveryState === 'FAILED' ? 'Send failed' : 'Send outcome unresolved' };
  const processing = message.processingState === 'RUNNING' || message.processingState === 'QUEUED'
    ? { icon: LoaderCircle, label: 'Professional processing' }
    : message.processingState === 'COMPLETED'
      ? { icon: Check, label: 'Professional response complete' }
      : { icon: Ban, label: `Professional processing ${message.processingState.toLowerCase()}` };
  const evidence = message.evidenceState === 'RECORDED' && Boolean(message.evidenceRecordId)
    ? { icon: CircleCheck, label: 'Evidence recorded', className: 'recorded' }
    : message.evidenceState === 'RECORDED'
      ? { icon: CircleAlert, label: 'Evidence pending verification', className: 'pending' }
    : message.evidenceState === 'PENDING'
      ? { icon: Clock3, label: 'Evidence pending', className: 'pending' }
      : { icon: CircleAlert, label: `Evidence ${message.evidenceState.toLowerCase().replaceAll('_', ' ')}`, className: '' };

  return (
    <div className="message-status" aria-label="Message status">
      {[{ ...delivery, className: '' }, { ...processing, className: '' }, evidence].map(({ icon: Icon, label, className }) => (
        <span className={className} key={label} title={label}><Icon aria-hidden="true" size={15} />{label}</span>
      ))}
    </div>
  );
}

export function ConversationExperience({ relationshipId, locale = 'en-IN' }: ConversationExperienceProps) {
  const [messages, setMessages] = useState<ConversationMessageV1[]>([]);
  const [authoritativeCursor, setAuthoritativeCursor] = useState('');
  const [nextCursor, setNextCursor] = useState<string>();
  const [unreadBoundary, setUnreadBoundary] = useState<string>();
  const [draft, setDraft] = useState('');
  const [queued, setQueued] = useState<QueuedContribution>();
  const [executionId, setExecutionId] = useState<string>();
  const [connection, setConnection] = useState<ConnectionState>('connecting');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [announcement, setAnnouncement] = useState('');

  const fetchTimeline = useCallback(async (options?: { cursor?: string; afterCursor?: string }) => {
    const search = new URLSearchParams({ limit: '40' });
    if (options?.cursor) search.set('cursor', options.cursor);
    if (options?.afterCursor) search.set('afterCursor', options.afterCursor);
    const response = await fetch(`/api/conversations/${encodeURIComponent(relationshipId)}?${search}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await readProblem(response));
    const page = ConversationTimelinePageV1FromJSON(await response.json());
    setMessages((current) => mergeMessages(options?.cursor || options?.afterCursor ? current : [], page.items));
    setAuthoritativeCursor(page.authoritativeCursor);
    setNextCursor(page.nextCursor);
    setUnreadBoundary(page.unreadBoundaryMessageId);
    const lastVisible = page.items.at(-1);
    if (page.unreadBoundaryMessageId && lastVisible) {
      void fetch(`/api/conversations/${encodeURIComponent(relationshipId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'read',
          idempotencyKey: crypto.randomUUID(),
          lastVisibleMessageId: lastVisible.messageId,
          authoritativeCursor: page.authoritativeCursor,
        }),
      });
    }
    return page;
  }, [relationshipId]);

  const submit = useCallback(async (contribution: QueuedContribution, cursor: string) => {
    if (!navigator.onLine) {
      setConnection('offline');
      return;
    }
    setSending(true);
    setError('');
    try {
      const response = await fetch(`/api/conversations/${encodeURIComponent(relationshipId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'send', ...contribution, locale, expectedCursor: cursor || undefined }),
      });
      if (!response.ok) throw new Error(await readProblem(response));
      const submission = ConversationSubmissionV1FromJSON(await response.json());
      setMessages((current) => mergeMessages(current.filter((item) => item.messageId !== contribution.clientMessageId), [submission.message]));
      setAuthoritativeCursor(submission.authoritativeCursor);
      setExecutionId(submission.executionId);
      localStorage.setItem(retryKey(relationshipId, submission.message.messageId), contribution.idempotencyKey);
      localStorage.removeItem(storageKey(relationshipId, 'outbox'));
      localStorage.removeItem(storageKey(relationshipId, 'draft'));
      setQueued(undefined);
      setDraft('');
      setAnnouncement('Message accepted. Professional processing is pending.');
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : 'The send outcome is unknown.';
      setError(message);
      setMessages((current) => current.map((item) => item.messageId === contribution.clientMessageId
        ? { ...item, deliveryState: 'UNRESOLVED' }
        : item));
    } finally {
      setSending(false);
    }
  }, [locale, relationshipId]);

  const reconcileContribution = useCallback(async (contribution: QueuedContribution, page: ConversationTimelinePageV1) => {
    const canonical = page.items.find((item) => item.clientMessageId === contribution.clientMessageId);
    if (canonical) {
      localStorage.removeItem(storageKey(relationshipId, 'outbox'));
      localStorage.removeItem(storageKey(relationshipId, 'draft'));
      setQueued(undefined);
      setDraft('');
      setAnnouncement('Message reconciled with the authoritative timeline.');
      return;
    }
    await submit(contribution, page.authoritativeCursor);
  }, [relationshipId, submit]);

  useEffect(() => {
    let active = true;
    const savedDraft = localStorage.getItem(storageKey(relationshipId, 'draft')) ?? '';
    const savedOutbox = localStorage.getItem(storageKey(relationshipId, 'outbox'));
    setDraft(savedDraft);
    setQueued(savedOutbox ? JSON.parse(savedOutbox) as QueuedContribution : undefined);
    setLoading(true);
    fetchTimeline()
      .then((page) => {
        if (!active || !savedOutbox || !navigator.onLine) return;
        return reconcileContribution(JSON.parse(savedOutbox) as QueuedContribution, page);
      })
      .catch((caught: unknown) => active && setError(caught instanceof Error ? caught.message : 'Conversation unavailable.'))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [fetchTimeline, reconcileContribution, relationshipId]);

  useEffect(() => {
    let disposed = false;
    let controller: AbortController | undefined;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let cursorExpiryReconciled = false;
    const streamUrl = `/api/conversations/${encodeURIComponent(relationshipId)}/stream`;

    const scheduleReconnect = () => {
      if (disposed) return;
      setConnection(navigator.onLine ? 'reconnecting' : 'offline');
      retryTimer = setTimeout(() => void connect(), 1000);
    };

    const handleEvent = async (event: ConversationStreamEventV1) => {
      if (event.eventId) localStorage.setItem(streamCursorKey(relationshipId), event.eventId);
      if (event.eventType === 'heartbeat') return;

      if (['message.completed', 'message.failed', 'stream.cancelled', 'stop.applied'].includes(event.eventType)) {
        setExecutionId((current) => {
          const terminalExecutionId = event.executionId ?? current;
          if (terminalExecutionId) localStorage.removeItem(cancellationKey(relationshipId, terminalExecutionId));
          return !event.executionId || event.executionId === current ? undefined : current;
        });
      } else if (event.executionId) {
        setExecutionId(event.executionId);
      }

      if (event.eventType === 'stop.applied') {
        setConnection('stopped');
        setAnnouncement('Emergency Stop applied. Stream rendering stopped.');
        controller?.abort();
        return;
      }
      if (event.eventType === 'reconciliation.required') {
        localStorage.removeItem(streamCursorKey(relationshipId));
        await fetchTimeline();
        controller?.abort();
        if (!disposed) void connect();
        return;
      }
      if (event.eventType === 'response.delta' && 'appendText' in event.data) {
        setAnnouncement(`Professional response updating: ${event.data.appendText}`);
      }
      await fetchTimeline().catch(() => setConnection('reconnecting'));
    };

    const connect = async () => {
      controller = new AbortController();
      const lastEventId = localStorage.getItem(streamCursorKey(relationshipId));
      const headers = new Headers({ Accept: 'text/event-stream' });
      if (lastEventId) headers.set('Last-Event-ID', lastEventId);
      try {
        const response = await fetch(streamUrl, { cache: 'no-store', headers, signal: controller.signal });
        if (response.status === 410) {
          if (cursorExpiryReconciled) {
            setError('Conversation stream history remains unavailable after reconciliation.');
            return;
          }
          cursorExpiryReconciled = true;
          localStorage.removeItem(streamCursorKey(relationshipId));
          await fetchTimeline();
          if (!disposed) void connect();
          return;
        }
        if (response.status === 423) {
          setConnection('stopped');
          setAnnouncement('Emergency Stop remains active. Stream reconnect is paused.');
          return;
        }
        if (!response.ok) {
          scheduleReconnect();
          return;
        }
        cursorExpiryReconciled = false;
        setConnection('live');
        await consumeEventStream(response, handleEvent);
        scheduleReconnect();
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === 'AbortError') return;
        scheduleReconnect();
      }
    };

    void connect();
    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      controller?.abort();
    };
  }, [fetchTimeline, relationshipId]);

  useEffect(() => {
    const reconnect = () => {
      setConnection('reconnecting');
      void fetchTimeline({ afterCursor: authoritativeCursor || undefined })
        .then((page) => queued ? reconcileContribution(queued, page) : undefined)
        .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : 'Reconciliation failed.'));
    };
    const offline = () => setConnection('offline');
    window.addEventListener('online', reconnect);
    window.addEventListener('offline', offline);
    return () => {
      window.removeEventListener('online', reconnect);
      window.removeEventListener('offline', offline);
    };
  }, [authoritativeCursor, fetchTimeline, queued, reconcileContribution]);

  function updateDraft(value: string) {
    setDraft(value);
    if (value) localStorage.setItem(storageKey(relationshipId, 'draft'), value);
    else localStorage.removeItem(storageKey(relationshipId, 'draft'));
  }

  async function sendMessage() {
    const text = draft.trim();
    if (!text || sending || queued) return;
    const contribution = { clientMessageId: crypto.randomUUID(), idempotencyKey: crypto.randomUUID(), text };
    localStorage.setItem(storageKey(relationshipId, 'outbox'), JSON.stringify(contribution));
    setQueued(contribution);
    setMessages((current) => mergeMessages(current, [{
      schemaVersion: '1.0',
      messageId: contribution.clientMessageId,
      relationshipId,
      sequence: (current.at(-1)?.sequence ?? 0) + 1,
      actor: 'CUSTOMER',
      channel: 'WEB',
      content: [{ schemaVersion: '1.0', blockType: 'TEXT', text }],
      cards: [],
      deliveryState: 'LOCAL_ONLY',
      processingState: 'NOT_STARTED',
      evidenceState: 'NOT_APPLICABLE',
      partial: false,
      clientMessageId: contribution.clientMessageId,
      acceptedAt: new Date(),
    }]));
    if (!navigator.onLine) {
      setConnection('offline');
      return;
    }
    const page = await fetchTimeline({ afterCursor: authoritativeCursor || undefined }).catch(() => undefined);
    if (page) await reconcileContribution(contribution, page);
  }

  async function retry(message: ConversationMessageV1) {
    setError('');
    const idempotencyKey = localStorage.getItem(retryKey(relationshipId, message.messageId));
    if (!idempotencyKey) {
      setError('Retry identity is unavailable on this device. Refresh before sending a new message.');
      return;
    }
    try {
      await fetchTimeline({ afterCursor: authoritativeCursor || undefined });
      const response = await fetch(`/api/conversations/${encodeURIComponent(relationshipId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'retry', messageId: message.messageId, idempotencyKey }),
      });
      if (!response.ok) throw new Error(await readProblem(response));
      const submission = ConversationSubmissionV1FromJSON(await response.json());
      setMessages((current) => mergeMessages(current, [submission.message]));
      setExecutionId(submission.executionId);
      setAnnouncement('Retry accepted for the original message.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Retry outcome is unknown.');
    }
  }

  async function cancel() {
    if (!executionId) return;
    const key = cancellationKey(relationshipId, executionId);
    const idempotencyKey = localStorage.getItem(key) ?? crypto.randomUUID();
    localStorage.setItem(key, idempotencyKey);
    const response = await fetch(`/api/conversations/${encodeURIComponent(relationshipId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'cancel', executionId, idempotencyKey }),
    });
    if (!response.ok) {
      setError(await readProblem(response));
      return;
    }
    setAnnouncement('Cancellation requested. Accepted partial content remains incomplete.');
    await fetchTimeline({ afterCursor: authoritativeCursor || undefined }).catch(() => undefined);
  }

  let previousDate = '';
  let previousChannel = '';
  return (
    <section className="conversation-experience" aria-labelledby="conversation-title">
      <header className="conversation-heading">
        <div><p className="section-label">Conversation</p><h2 id="conversation-title">Work with your professional</h2></div>
        <span className={`connection-state connection-${connection}`}>
          {connection === 'offline' ? <WifiOff aria-hidden="true" size={16} /> : null}
          {connection.replaceAll('_', ' ')}
        </span>
      </header>

      {nextCursor ? <button className="load-older" onClick={() => void fetchTimeline({ cursor: nextCursor })} type="button">Load earlier messages</button> : null}
      <div className="conversation-timeline" aria-busy={loading} aria-label="Conversation timeline">
        {loading ? <p className="conversation-empty"><LoaderCircle aria-hidden="true" className="spin" /> Loading conversation…</p> : null}
        {!loading && messages.length === 0 ? <p className="conversation-empty">No messages yet. Start with a clear outcome for your professional.</p> : null}
        {messages.map((message) => {
          const date = message.acceptedAt.toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
          const showDate = date !== previousDate;
          const showChannel = message.channel !== previousChannel;
          previousDate = date;
          previousChannel = message.channel;
          return (
            <div key={message.messageId}>
              {showDate ? <p className="conversation-separator"><span>{date}</span></p> : null}
              {showChannel ? <p className="channel-separator">{message.channel.toLowerCase()} channel</p> : null}
              {message.messageId === unreadBoundary ? <p className="unread-boundary">Unread messages</p> : null}
              <article className={`conversation-message message-${message.actor.toLowerCase()}`}>
                <div className="message-meta"><strong>{message.actor === 'CUSTOMER' ? 'You' : message.actor === 'PROFESSIONAL' ? 'Your professional' : 'WAOOAW'}</strong><span>{message.channel}</span></div>
                {message.content.map((block, index) => <p key={`${message.messageId}-${index}`}>{block.text}</p>)}
                {message.partial ? <p className="partial-disclosure">Incomplete response · {message.completionReason?.replaceAll('_', ' ') ?? 'still changing'}</p> : null}
                {message.cards.map((card) => (
                  <Card
                    canRetry={message.deliveryState === 'FAILED' || message.deliveryState === 'UNRESOLVED'}
                    card={card}
                    key={card.cardId}
                    onRetry={() => void retry(message)}
                  />
                ))}
                <MessageStatus message={message} />
                {message.deliveryState === 'FAILED' || message.deliveryState === 'UNRESOLVED' ? (
                  <button className="retry-command" onClick={() => void retry(message)} type="button"><RotateCcw aria-hidden="true" size={16} />Retry original message</button>
                ) : null}
              </article>
            </div>
          );
        })}
      </div>

      <form className="conversation-composer" onSubmit={(event) => { event.preventDefault(); void sendMessage(); }}>
        <label htmlFor={`conversation-draft-${relationshipId}`}>Message your professional</label>
        <textarea
          disabled={connection === 'stopped'}
          id={`conversation-draft-${relationshipId}`}
          maxLength={32000}
          onChange={(event) => updateDraft(event.target.value)}
          placeholder="Describe the outcome you need"
          rows={3}
          value={draft}
        />
        <div className="composer-commands">
          <span>{connection === 'offline' || queued ? 'Draft retained on this device until reconciliation.' : 'Enter sends only with the Send button.'}</span>
          {executionId ? <button className="cancel-command" onClick={() => void cancel()} type="button"><Square aria-hidden="true" size={16} />Cancel response</button> : null}
          <button className="send-command" disabled={!draft.trim() || sending || Boolean(queued) || connection === 'stopped'} type="submit">
            {sending ? <LoaderCircle aria-hidden="true" className="spin" size={18} /> : <Send aria-hidden="true" size={18} />}
            {queued && connection === 'offline' ? 'Queued' : sending ? 'Sending' : 'Send'}
          </button>
        </div>
      </form>
      {error ? <p className="conversation-error" role="alert">{error}</p> : null}
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">{announcement}</p>
    </section>
  );
}