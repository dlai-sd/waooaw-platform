'use client';

// Implements: WC-134 R005; identity-boundary.md Section 6.3.
// Constitutional basis: C-023, C-026, C-059, C-063

import { useCallback, useEffect, useRef, useState } from 'react';
import { SignOutCommand } from '@/components/auth/SignOutCommand';
import { WhatsAppPhoneChange } from './WhatsAppPhoneChange';

type Command = 'START' | 'APPROVE' | 'CANCEL' | 'STATUS';
type LinkState = {
  linkId: string;
  state: string;
  maskedMobile: string;
  expiresAt: string;
  whatsAppConfirmation?: string | null;
};

type RelationshipChoice = { relationshipId: string; label: string };
type BindingResponse = {
  relationshipId: string;
  bindingId: string;
  channel: 'WHATSAPP';
  status: 'ACTIVE';
  assurance: 'TIER_4_PORTAL_FRESH';
};

const savedLinkStorageKey = 'waooaw:whatsapp-account-link-id';

function isLinkState(value: unknown): value is LinkState {
  return (
    value !== null &&
    typeof value === 'object' &&
    'linkId' in value &&
    typeof value.linkId === 'string' &&
    'state' in value &&
    typeof value.state === 'string' &&
    [
      'PENDING_PORTAL_APPROVAL',
      'PENDING_WHATSAPP_CONFIRMATION',
      'LINKED',
      'EXPIRED',
      'CANCELLED',
      'DUPLICATE_RESOLUTION_REQUIRED',
    ].includes(value.state) &&
    'maskedMobile' in value &&
    typeof value.maskedMobile === 'string' &&
    'expiresAt' in value &&
    typeof value.expiresAt === 'string' &&
    Number.isFinite(Date.parse(value.expiresAt)) &&
    (value.state !== 'PENDING_WHATSAPP_CONFIRMATION' ||
      ('whatsAppConfirmation' in value &&
        typeof value.whatsAppConfirmation === 'string' &&
        value.whatsAppConfirmation.startsWith('LINK ') &&
        value.whatsAppConfirmation.length <= 3077)) &&
    (!('whatsAppConfirmation' in value) ||
      value.whatsAppConfirmation === null ||
      typeof value.whatsAppConfirmation === 'string')
  );
}

function isBindingResponse(value: unknown, relationshipId: string): value is BindingResponse {
  return (
    value !== null &&
    typeof value === 'object' &&
    'relationshipId' in value &&
    value.relationshipId === relationshipId &&
    'bindingId' in value &&
    typeof value.bindingId === 'string' &&
    'channel' in value &&
    value.channel === 'WHATSAPP' &&
    'status' in value &&
    value.status === 'ACTIVE' &&
    'assurance' in value &&
    value.assurance === 'TIER_4_PORTAL_FRESH'
  );
}

export function WhatsAppAccountLink({
  relationships = [],
  relationshipsUnavailable = false,
}: {
  relationships?: RelationshipChoice[];
  relationshipsUnavailable?: boolean;
}) {
  const [link, setLink] = useState<LinkState>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [selectedRelationshipId, setSelectedRelationshipId] = useState('');
  const [consent, setConsent] = useState(false);
  const [bindingBusy, setBindingBusy] = useState(false);
  const [bindingError, setBindingError] = useState('');
  const [boundRelationships, setBoundRelationships] = useState<Record<string, string>>({});
  const keys = useRef<Partial<Record<Command, string>>>({});
  const restoredLink = useRef(false);

  const command = useCallback(
    async (action: Command, linkIdOverride?: string) => {
      if (busy) return;
      const linkId = linkIdOverride ?? link?.linkId;
      if (action !== 'START' && !linkId) return;
      setBusy(true);
      setError('');
      keys.current[action] ??= crypto.randomUUID();
      try {
        const response = await fetch('/api/identity/account-links', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          cache: 'no-store',
          body: JSON.stringify({
            command: action,
            idempotencyKey: keys.current[action],
            ...(linkId ? { linkId } : {}),
          }),
        });
        if (!response.ok) {
          if (response.status === 404 && linkIdOverride) sessionStorage.removeItem(savedLinkStorageKey);
          if (response.status === 410)
            setLink((current) => (current ? { ...current, state: 'EXPIRED', whatsAppConfirmation: null } : current));
          if (response.status === 403) {
            const failure: unknown = await response.json();
            setError(
              failure !== null &&
                typeof failure === 'object' &&
                'code' in failure &&
                failure.code === 'IDENTITY_STEP_UP_REQUIRED'
                ? 'fresh-sign-in'
                : 'denied'
            );
            return;
          }
          setError(
            response.status === 401
              ? 'fresh-sign-in'
              : response.status === 410
                ? 'expired'
                : response.status === 429
                  ? 'limited'
                  : 'unavailable'
          );
          return;
        }
        const value: unknown = await response.json();
        if (!isLinkState(value)) throw new Error('Account-link response is invalid.');
        setLink(value);
        if (value.state === 'EXPIRED' || value.state === 'CANCELLED') sessionStorage.removeItem(savedLinkStorageKey);
        else sessionStorage.setItem(savedLinkStorageKey, value.linkId);
      } catch {
        setError('unavailable');
      } finally {
        setBusy(false);
      }
    },
    [busy, link]
  );

  useEffect(() => {
    if (restoredLink.current) return;
    restoredLink.current = true;
    const savedLinkId = sessionStorage.getItem(savedLinkStorageKey);
    if (savedLinkId) void command('STATUS', savedLinkId);
  }, [command]);

  function restart() {
    keys.current = {};
    setLink(undefined);
    setError('');
    sessionStorage.removeItem(savedLinkStorageKey);
  }

  async function attachToRelationship() {
    if (bindingBusy || link?.state !== 'LINKED' || !selectedRelationshipId || !consent) return;
    setBindingBusy(true);
    setBindingError('');
    try {
      const response = await fetch(
        `/api/relationships/${encodeURIComponent(selectedRelationshipId)}/whatsapp-channel`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          cache: 'no-store',
          body: JSON.stringify({
            identityAccountLinkId: link.linkId,
            consentToRelationshipChannel: true,
          }),
        }
      );
      const value: unknown = await response.json();
      if (!response.ok) {
        const code = value !== null && typeof value === 'object' && 'code' in value ? value.code : undefined;
        setBindingError(
          code === 'IDENTITY_STEP_UP_REQUIRED'
            ? 'fresh-sign-in'
            : code === 'IDENTITY_RESOURCE_NOT_ACCESSIBLE'
              ? 'identity'
              : code === 'IDENTITY_ACTION_DENIED'
                ? 'denied'
                : code === 'RELATIONSHIP_WORKSPACE_BLOCKED'
                  ? 'stopped'
                  : 'unavailable'
        );
        return;
      }
      if (!isBindingResponse(value, selectedRelationshipId))
        throw new Error('WhatsApp channel-binding response is invalid.');
      setBoundRelationships((current) => ({
        ...current,
        [value.relationshipId]: value.bindingId,
      }));
      setConsent(false);
    } catch {
      setBindingError('unavailable');
    } finally {
      setBindingBusy(false);
    }
  }

  return (
    <section aria-labelledby="whatsapp-link-heading">
      <WhatsAppPhoneChange
        onCompleted={() => {
          restart();
          setBoundRelationships({});
          setSelectedRelationshipId('');
          setConsent(false);
        }}
      />
      <h2 id="whatsapp-link-heading">Connect your WhatsApp number</h2>
      <p>
        Use your verified registration number. Linking does not sign you in, create employment, or move your guest chat
        into account history.
      </p>
      {!link ? (
        <button className="primary-command" type="button" disabled={busy} onClick={() => void command('START')}>
          Start WhatsApp link
        </button>
      ) : (
        <>
          <p>Number: {link.maskedMobile}</p>
          {link.state === 'PENDING_PORTAL_APPROVAL' ? (
            <button className="primary-command" type="button" disabled={busy} onClick={() => void command('APPROVE')}>
              Approve linking this number to my account
            </button>
          ) : link.state === 'PENDING_WHATSAPP_CONFIRMATION' ? (
            <>
              <p>
                Message WAOOAW from this number, review the Privacy Notice and reply YES if asked. Then copy and send
                the exact message below before {new Date(link.expiresAt).toLocaleString()}. Guest service hours and
                message limits still apply.
              </p>
              <textarea aria-label="WhatsApp confirmation message" readOnly value={link.whatsAppConfirmation ?? ''} />
            </>
          ) : link.state === 'LINKED' ? (
            <p>
              <output>
                Your number is linked. Relationship channel access still requires separate approval in the secure
                portal.
              </output>
            </p>
          ) : (
            <p>
              <output>This link request is no longer available.</output>
            </p>
          )}
          {link.state === 'PENDING_PORTAL_APPROVAL' || link.state === 'PENDING_WHATSAPP_CONFIRMATION' ? (
            <>
              <button type="button" disabled={busy} onClick={() => void command('STATUS')}>
                Check link status
              </button>
              <button type="button" disabled={busy} onClick={() => void command('CANCEL')}>
                Cancel this link request
              </button>
            </>
          ) : link.state !== 'LINKED' ? (
            <button type="button" disabled={busy} onClick={restart}>
              Start a new link request
            </button>
          ) : null}
        </>
      )}
      {link?.state === 'LINKED' ? (
        <section aria-labelledby="whatsapp-channel-approval-heading">
          <h3 id="whatsapp-channel-approval-heading">Approve relationship channel access</h3>
          {relationshipsUnavailable ? (
            <p role="alert">
              Your relationships could not be loaded. No channel access was changed; refresh the page and try again.
            </p>
          ) : relationships.length === 0 ? (
            <p>There are no active or trial relationships available for channel approval.</p>
          ) : (
            <>
              <label htmlFor="whatsapp-relationship">Choose an active relationship</label>
              <select
                id="whatsapp-relationship"
                value={selectedRelationshipId}
                onChange={(event) => {
                  setSelectedRelationshipId(event.target.value);
                  setConsent(false);
                  setBindingError('');
                }}
              >
                <option value="">Select a relationship</option>
                {relationships.map((relationship) => (
                  <option key={relationship.relationshipId} value={relationship.relationshipId}>
                    {relationship.label}
                  </option>
                ))}
              </select>
              {selectedRelationshipId ? (
                boundRelationships[selectedRelationshipId] ? (
                  <p>
                    <output>WhatsApp is connected to this relationship. Guest history was not transferred.</output>
                  </p>
                ) : (
                  <>
                    <label>
                      <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
                      I approve WhatsApp messages for this relationship. I understand guest history will not be
                      transferred.
                    </label>
                    <button
                      className="primary-command"
                      type="button"
                      disabled={bindingBusy || !consent}
                      onClick={() => void attachToRelationship()}
                    >
                      {bindingBusy ? 'Approving channel access...' : 'Approve WhatsApp channel access'}
                    </button>
                  </>
                )
              ) : null}
            </>
          )}
          {bindingError ? (
            <div role="alert">
              <p>
                {bindingError === 'fresh-sign-in'
                  ? 'A fresh sign-in is required before approving channel access.'
                  : bindingError === 'identity'
                    ? 'This verified WhatsApp link is not available to the current account.'
                    : bindingError === 'denied'
                      ? 'Channel access was denied. No relationship binding was created.'
                      : bindingError === 'stopped'
                        ? 'This relationship is currently blocked from channel access.'
                        : 'Channel access could not be confirmed. Retry only after checking the relationship status.'}
              </p>
              {bindingError === 'fresh-sign-in' ? <SignOutCommand label="Sign out to sign in again" /> : null}
            </div>
          ) : null}
        </section>
      ) : null}
      {busy ? (
        <p>
          <output>Checking your account link...</output>
        </p>
      ) : null}
      {error ? (
        <div role="alert">
          <p>
            {error === 'fresh-sign-in'
              ? 'A fresh sign-in is required. Sign out and sign in again, then return to your profile.'
              : error === 'denied'
                ? 'Your current account cannot confirm this link. No account access was granted.'
                : error === 'expired'
                  ? 'This request expired. Start a new link request.'
                  : error === 'limited'
                    ? 'Too many requests. Wait before trying again.'
                    : 'The account link could not be completed. Retry the same action; no new request is sent automatically.'}
          </p>
          {error === 'fresh-sign-in' ? <SignOutCommand label="Sign out to sign in again" /> : null}
        </div>
      ) : null}
    </section>
  );
}
