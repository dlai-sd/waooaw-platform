import { createServer } from 'node:http';

const primaryRelationshipId = 'relationship-active';
const executionId = '3ead2d21-f908-40b5-9510-b1e77f516d7e';
const streamClients = new Map();
const scopedTimelines = new Map();
const continuityStates = new Map();
const voiceSessions = new Map();
const identityProviderDelayMs = Number.parseInt(process.env.IDENTITY_PROVIDER_DELAY_MS ?? '0', 10) || 0;

const governedCards = [
  {
    schemaVersion: '1.0', cardId: 'card-plan', cardType: 'PLAN', owner: 'SHARED', state: 'ACTIVE',
    effect: 'Sets the next agreed outcome.', goal: 'Increase qualified enquiries', progressState: 'ON_TRACK',
    commands: [{ commandId: 'VIEW_PLAN', label: 'View plan', availability: 'AVAILABLE', unavailableReason: 'Plan workspace is not available in this release.' }],
  },
  {
    schemaVersion: '1.0', cardId: 'card-action', cardType: 'ACTION', owner: 'CUSTOMER', state: 'READY',
    effect: 'Starts approved customer work.', goal: 'Approve the brief', commands: [],
  },
  {
    schemaVersion: '1.0', cardId: 'card-deliverable', cardType: 'DELIVERABLE', owner: 'PROFESSIONAL', state: 'DRAFT',
    effect: 'Makes the draft available for review.', title: 'Campaign brief', deliverableState: 'REVIEW', commands: [],
  },
  {
    schemaVersion: '1.0', cardId: 'card-decision', cardType: 'DECISION', owner: 'SHARED', state: 'OPEN',
    effect: 'Changes the approved campaign direction.', decisionState: 'CUSTOMER_INPUT_REQUIRED',
    authorityImpact: 'No work starts before selection.', alternatives: [{ alternativeId: 'A', label: 'Continue', effect: 'Uses the approved brief.' }], commands: [],
  },
];

function relationship(relationshipId) {
  return {
    relationshipId,
    professionalType: relationshipId === 'relationship-second' ? 'PRIVATE_TUTOR' : 'DIGITAL_MARKETING',
    state: relationshipId === 'relationship-contract' ? 'CONTRACT_PENDING_ACCEPTANCE' : 'ACTIVE', stateVersion: 2,
    createdAt: '2026-08-08T10:00:00.000Z', updatedAt: '2026-08-09T10:00:00.000Z',
  };
}

function message(relationshipId, overrides = {}) {
  return {
    schemaVersion: '1.0', messageId: `message-${relationshipId}`, relationshipId, sequence: 1,
    actor: 'PROFESSIONAL', channel: 'WEB',
    content: [{ schemaVersion: '1.0', blockType: 'TEXT', text: 'Here is the current plan.' }],
    cards: governedCards, deliveryState: 'ACCEPTED', processingState: 'RUNNING', evidenceState: 'PENDING',
    partial: true, completionReason: 'PARTIAL_FAILURE', acceptedAt: '2026-08-10T09:00:00.000Z', ...overrides,
  };
}

function initialMessages(relationshipId) {
  if (relationshipId === primaryRelationshipId) return [message(primaryRelationshipId)];
  if (relationshipId === 'relationship-evidence') return [message(relationshipId, { cards: [], partial: false, processingState: 'COMPLETED' })];
  if (relationshipId === 'relationship-stream') return [message(relationshipId, { cards: [], content: [{ schemaVersion: '1.0', blockType: 'TEXT', text: 'Draft response retained.' }] })];
  if (relationshipId === 'relationship-retry') return [message(relationshipId, { cards: [], partial: false, deliveryState: 'UNRESOLVED', processingState: 'FAILED', evidenceState: 'FAILED' })];
  return [];
}

function scopeFor(request) {
  return request.headers.authorization ?? 'fixture-anonymous';
}

function scopeKey(scope, relationshipId) {
  return `${scope}:${relationshipId}`;
}

function continuityFor(scope, relationshipId) {
  const key = scopeKey(scope, relationshipId);
  if (!continuityStates.has(key)) continuityStates.set(key, { stopped: false, handoffs: new Map() });
  return continuityStates.get(key);
}

function messagesFor(scope, relationshipId) {
  const key = scopeKey(scope, relationshipId);
  if (!scopedTimelines.has(key)) scopedTimelines.set(key, initialMessages(relationshipId));
  return scopedTimelines.get(key);
}

function setMessages(scope, relationshipId, messages) {
  scopedTimelines.set(scopeKey(scope, relationshipId), messages);
}

function timeline(scope, relationshipId) {
  const messages = messagesFor(scope, relationshipId);
  return {
    schemaVersion: '1.0', relationshipId, items: messages,
    authoritativeCursor: `cursor-${relationshipId}-${messages.length}`,
    hasMore: false, serverTime: '2026-08-10T10:01:00.000Z',
  };
}

function event(relationshipId, eventType, overrides = {}) {
  return {
    schemaVersion: '1.0', eventId: `event-${relationshipId}-${eventType}`, eventType, relationshipId,
    sequence: 2, occurredAt: '2026-08-10T10:01:00.000Z', data: {}, ...overrides,
  };
}

function sendEvent(scope, relationshipId, payload) {
  for (const response of streamClients.get(scopeKey(scope, relationshipId)) ?? []) response.write(`data: ${JSON.stringify(payload)}\n\n`);
}

function readBody(request) {
  return new Promise((resolve, reject) => {
    let body = '';
    request.on('data', (chunk) => { body += chunk; });
    request.on('end', () => {
      try { resolve(body ? JSON.parse(body) : {}); } catch (error) { reject(error); }
    });
    request.on('error', reject);
  });
}

function json(response, body, status = 200) {
  response.statusCode = status;
  response.setHeader('Content-Type', 'application/json');
  response.end(JSON.stringify(body));
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? '/', 'http://127.0.0.1:5001');
  const scope = scopeFor(request);
  const policyDenied = request.headers.authorization?.startsWith('Bearer fixture-policy-denied-') === true;
  const relationshipMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)$/);
  const timelineMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/timeline$/);
  const messagesMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/messages$/);
  const retryMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/messages\/([^/]+)\/retry$/);
  const readMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/read-position$/);
  const streamMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/stream$/);
  const cancelMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/executions\/([^/]+)$/);
  const workspaceMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/workspace(?:\/(plan|attention|work|results|usage-budget|rights-controls|evidence))?$/);
  const configurationMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/workspace\/configuration$/);
  const goalsMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/workspace\/goals$/);
  const outcomesMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/workspace\/business-outcomes$/);
  const operationsMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/workspace\/operations$/);
  const onboardMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/workspace\/configuration\/onboard$/);
  const alertMutationMatch = url.pathname.match(/^\/api\/v1\/notifications\/alerts\/([^/]+)\/(read|acknowledge)$/);
  const evaluationMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/evaluation$/);
  const contractJourneyMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/contract-journey$/);
  const prepareHandoffMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/handoffs$/);
  const activateHandoffMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/handoffs\/([^/]+)\/activate$/);
  const stopRelationshipMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/emergency-stop$/);
  const voiceCreateMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/voice-contributions\/sessions$/);
  const voiceSessionMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/voice-contributions\/sessions\/([^/]+)$/);
  const voiceAudioMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/voice-contributions\/sessions\/([^/]+)\/audio$/);
  const voiceTranscriptMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/voice-contributions\/sessions\/([^/]+)\/transcript$/);
  const voiceCorrectionMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/voice-contributions\/sessions\/([^/]+)\/correction$/);
  const voiceSendMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/voice-contributions\/sessions\/([^/]+)\/send$/);
  const voiceCancelMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/voice-contributions\/sessions\/([^/]+)\/cancel$/);

  if (request.method === 'GET' && url.pathname === '/api/v1/identity/providers') {
    if (identityProviderDelayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, identityProviderDelayMs));
    }
    json(response, { providers: [
      { id: 'GOOGLE', displayName: 'Google', authenticationPath: 'GOOGLE', availability: 'AVAILABLE' },
      { id: 'FACEBOOK', displayName: 'Facebook', authenticationPath: 'META', availability: 'UNAVAILABLE', unavailableReason: 'NOT_CONFIGURED' },
      { id: 'APPLE', displayName: 'Apple', authenticationPath: 'APPLE', availability: 'UNAVAILABLE', unavailableReason: 'NOT_CONFIGURED' },
      { id: 'EMAIL', displayName: 'Email', authenticationPath: 'CREDENTIAL', availability: 'AVAILABLE' },
    ] });
    return;
  }

  if (request.method === 'GET' && url.pathname === '/api/v1/identity/session') {
    if (policyDenied) {
      json(response, { code: 'IDENTITY_ACTION_DENIED' }, 403);
      return;
    }
    json(response, { accountReference: 'account-fixture', roles: ['OWNER'], capabilities: ['READ_ACCOUNT', 'MANAGE_ROUTINE_ACTIONS', 'HIRE_PROFESSIONAL'], assuranceLevel: 'AAL2_ACCOUNT', authenticationPath: 'PORTAL', emailVerified: true, mobileVerified: false, authenticatedAt: '2026-08-12T09:00:00Z', expiresAt: '2099-08-12T10:00:00Z', nextAction: 'NONE' });
    return;
  }

  if (request.method === 'POST' && url.pathname === '/api/v1/identity/registrations' && policyDenied) {
    json(response, { code: 'IDENTITY_ACTION_DENIED' }, 403);
    return;
  }

  if (request.method === 'GET' && url.pathname === '/api/v1/identity/profile') {
    json(response, { schemaVersion: '1.0.0', displayName: 'Asha Rao', organizationDisplayName: 'Acme Clinic', email: 'as***@example.test', emailVerified: true, mobileVerified: false, activeRole: 'OWNER', switchableAccounts: [], updatedAt: '2026-08-12T10:00:00Z' });
    return;
  }

  if (request.method === 'PUT' && url.pathname === '/api/v1/identity/profile') {
    const body = await readBody(request);
    json(response, { schemaVersion: '1.0.0', displayName: body.displayName, organizationDisplayName: body.organizationDisplayName, email: 'as***@example.test', emailVerified: true, mobileVerified: false, activeRole: 'OWNER', switchableAccounts: [], updatedAt: '2026-08-12T10:05:00Z' });
    return;
  }

  if (request.method === 'GET' && url.pathname === '/api/v1/identity/settings') {
    json(response, { schemaVersion: '1.0.0', locale: 'en-IN', theme: 'SYSTEM', timestampVisibility: 'RELATIVE', notificationPreferences: { approvalRequests: ['WEB'], maturityReports: ['EMAIL'], monthlyNarratives: ['EMAIL'], selfGovernanceAlerts: ['WEB', 'EMAIL'] }, availableSecurityActions: ['STEP_UP', 'CHANGE_PASSWORDLESS_METHODS'], updatedAt: '2026-08-12T10:00:00Z' });
    return;
  }

  if (request.method === 'PUT' && url.pathname === '/api/v1/identity/settings') {
    const body = await readBody(request);
    json(response, { ...body, availableSecurityActions: ['STEP_UP', 'CHANGE_PASSWORDLESS_METHODS'], updatedAt: '2026-08-12T10:05:00Z' });
    return;
  }

  if (request.method === 'GET' && url.pathname === '/api/v1/identity/login-methods') {
    json(response, { schemaVersion: '1.0.0', items: [{ provider: 'GOOGLE', state: 'ACTIVE', maskedIdentifier: 'as***@example.test' }, { provider: 'EMAIL', state: 'AVAILABLE_TO_LINK' }] });
    return;
  }

  if (request.method === 'GET' && url.pathname === '/api/v1/employment/relationships') {
    json(response, { schemaVersion: '1.0.0', producedAt: '2026-08-12T10:00:00Z', items: [{ relationshipId: primaryRelationshipId, professionalType: 'DIGITAL_MARKETING', professionalDisplayName: 'Mira', lifecycleState: 'ACTIVE', currentGoalSummary: 'Increase qualified enquiries', unreadState: 'ACTION_REQUIRED', availabilityState: 'AVAILABLE', currencyState: 'CURRENT', lastAuthoritativelyConfirmedAt: '2026-08-12T09:55:00Z', resumeTarget: { surface: 'CONVERSATION', relationshipId: primaryRelationshipId } }] });
    return;
  }

  if (request.method === 'GET' && url.pathname === '/api/v1/professionals/marketplace') {
    json(response, { schemaVersion: '1.0.0', producedAt: '2026-08-12T10:00:00Z', items: [{ professionalType: 'DIGITAL_MARKETING', version: '2.1.0', displayName: 'Digital Marketing Professional', suitability: ['Campaign planning', 'Performance review'], eligibility: { eligible: true, explanation: 'Available to this organization.' }, indicativePrice: { currency: 'INR', amountInrPaise: 118000, cadence: 'MONTHLY', qualification: 'Final terms follow configuration.' }, offerabilityState: 'OFFERABLE', trialTerms: '14-day governed trial', nextAction: 'START_TRIAL' }] });
    return;
  }

  if (request.method === 'GET' && url.pathname === '/api/v1/notifications/alerts') {
    json(response, { schemaVersion: '1.0.0', producedAt: '2026-08-12T10:00:00Z', items: [{ alertId: 'alert-action-1', version: '1', alertType: 'ACTIONABLE', severity: 'HIGH', source: 'RELATIONSHIP_ATTENTION', relationshipId: primaryRelationshipId, occurredAt: '2026-08-12T09:30:00Z', dueMeaning: 'Review the pending relationship decision.', readState: 'UNREAD', destination: { surface: 'WORK', relationshipId: primaryRelationshipId }, availableAction: 'ACKNOWLEDGE' }, { alertId: 'alert-info-1', version: '1', alertType: 'INFORMATIONAL', severity: 'LOW', source: 'RESULT', relationshipId: primaryRelationshipId, occurredAt: '2026-08-11T09:30:00Z', readState: 'READ', destination: { surface: 'RESULTS', relationshipId: primaryRelationshipId }, availableAction: 'NONE' }] });
    return;
  }

  if (request.method === 'POST' && alertMutationMatch) {
    const body = await readBody(request);
    json(response, { alertId: decodeURIComponent(alertMutationMatch[1]), version: String(Number(body.expectedAlertVersion) + 1), alertType: 'ACTIONABLE', severity: 'HIGH', source: 'RELATIONSHIP_ATTENTION', relationshipId: primaryRelationshipId, occurredAt: '2026-08-12T09:30:00Z', dueMeaning: 'Review the pending relationship decision.', readState: alertMutationMatch[2] === 'acknowledge' ? 'ACKNOWLEDGED' : 'READ', destination: { surface: 'WORK', relationshipId: primaryRelationshipId }, availableAction: alertMutationMatch[2] === 'acknowledge' ? 'NONE' : 'ACKNOWLEDGE' });
    return;
  }

  if (request.method === 'PUT' && onboardMatch) {
    await readBody(request);
    json(response, { sectionType: 'CONFIGURATION', currencyState: 'CURRENT', provenance: { source: 'BUSINESS_PLATFORM', producedAt: '2026-08-12T10:05:00Z' }, lifecyclePhase: 'INDUCT', items: [{ stepKey: 'ONBOARD', label: 'Onboard', state: 'COMPLETE', summary: 'Presentation preferences saved.' }, { stepKey: 'INDUCT', label: 'Induct', state: 'CURRENT', summary: 'Continue in conversation.' }] });
    return;
  }

  if (request.method === 'POST' && voiceCreateMatch) {
    const relationshipId = decodeURIComponent(voiceCreateMatch[1]);
    const body = await readBody(request);
    const sessionId = `voice-${relationshipId}`;
    voiceSessions.set(scopeKey(scope, sessionId), { relationshipId, locale: body.locale, version: 1, text: 'Please review this governed voice draft.' });
    json(response, {
      schemaVersion: '1.0.0', sessionId, relationshipId, state: 'CAPTURE_PENDING', locale: body.locale,
      allowedCommands: ['UPLOAD', 'CANCEL'], createdAt: '2026-08-12T10:00:00Z', updatedAt: '2026-08-12T10:00:00Z',
    }, 201);
    return;
  }
  if (request.method === 'GET' && voiceSessionMatch) {
    const sessionId = decodeURIComponent(voiceSessionMatch[2]);
    const session = voiceSessions.get(scopeKey(scope, sessionId));
    if (!session) { json(response, { title: 'not_authorized' }, 404); return; }
    json(response, { schemaVersion: '1.0.0', sessionId, relationshipId: session.relationshipId, state: 'REVIEW_REQUIRED', locale: session.locale, confidenceBand: 'REVIEW', allowedCommands: ['CORRECT', 'SEND', 'CANCEL'], createdAt: '2026-08-12T10:00:00Z', updatedAt: '2026-08-12T10:01:00Z' });
    return;
  }
  if (request.method === 'POST' && voiceAudioMatch) {
    const sessionId = decodeURIComponent(voiceAudioMatch[2]);
    if (!voiceSessions.has(scopeKey(scope, sessionId))) { json(response, { title: 'not_authorized' }, 404); return; }
    request.resume();
    request.on('end', () => json(response, { schemaVersion: '1.0.0', sessionId, state: 'REVIEW_REQUIRED', receiptId: '44444444-4444-4444-8444-444444444444', acceptedAt: '2026-08-12T10:01:00Z' }, 202));
    return;
  }
  if (request.method === 'GET' && voiceTranscriptMatch) {
    const sessionId = decodeURIComponent(voiceTranscriptMatch[2]);
    const session = voiceSessions.get(scopeKey(scope, sessionId));
    if (!session) { json(response, { title: 'not_authorized' }, 404); return; }
    json(response, { schemaVersion: '1.0.0', sessionId, state: 'REVIEW_REQUIRED', locale: session.locale, confidenceBand: 'REVIEW', text: session.text, version: session.version });
    return;
  }
  if (request.method === 'PUT' && voiceCorrectionMatch) {
    const sessionId = decodeURIComponent(voiceCorrectionMatch[2]);
    const session = voiceSessions.get(scopeKey(scope, sessionId));
    if (!session) { json(response, { title: 'not_authorized' }, 404); return; }
    const body = await readBody(request);
    session.text = body.correctedText;
    session.version += 1;
    json(response, { schemaVersion: '1.0.0', sessionId, state: 'READY_TO_SEND', version: session.version, recordedAt: '2026-08-12T10:02:00Z' });
    return;
  }
  if (request.method === 'POST' && voiceSendMatch) {
    const sessionId = decodeURIComponent(voiceSendMatch[2]);
    const session = voiceSessions.get(scopeKey(scope, sessionId));
    if (!session) { json(response, { title: 'not_authorized' }, 404); return; }
    json(response, { schemaVersion: '1.0.0', sessionId, contributionId: '55555555-5555-4555-8555-555555555555', state: 'RECORDED', evidenceReference: '66666666-6666-4666-8666-666666666666', reconciliationRequired: false, outcomeAt: '2026-08-12T10:03:00Z' });
    return;
  }
  if (request.method === 'POST' && voiceCancelMatch) {
    json(response, { schemaVersion: '1.0.0', sessionId: decodeURIComponent(voiceCancelMatch[2]), state: 'CANCELLED', reconciliationRequired: false, outcomeAt: '2026-08-12T10:03:00Z' });
    return;
  }

  if (request.method === 'POST' && prepareHandoffMatch) {
    const relationshipId = decodeURIComponent(prepareHandoffMatch[1]);
    const state = continuityFor(scope, relationshipId);
    const body = await readBody(request);
    const idempotencyKey = request.headers['idempotency-key'];
    if (state.stopped) {
      json(response, { code: 'RELATIONSHIP_STOPPED', title: 'Emergency Stop is active.' }, 409);
      return;
    }
    const prior = [...state.handoffs.values()].find((handoff) => handoff.idempotencyKey === idempotencyKey);
    if (prior) {
      if (prior.requestHash !== JSON.stringify(body)) {
        json(response, { code: 'IDEMPOTENCY_CONFLICT', title: 'The handoff request differs from the committed request.' }, 409);
        return;
      }
      json(response, { ...prior.response, replayed: true });
      return;
    }
    const handoffId = `handoff-${state.handoffs.size + 1}`;
    const envelope = {
      schemaVersion: '1.0', tenantId: 'fixture-tenant', relationshipId,
      participantId: 'fixture-participant', participantRole: 'EMPLOYER', sourceChannel: 'WHATSAPP',
      sourceConversationId: 'whatsapp-conversation', targetChannel: body.targetChannel,
      assuranceLevel: 'TIER_4_PORTAL_FRESH', authorityVersion: 2,
      continuityCheckpointId: `checkpoint-${state.handoffs.size + 1}`, idempotencyKey,
      expiresAt: '2026-08-10T10:15:00.000Z', integritySignature: 'fixture-valid-signature',
    };
    const prepared = { handoffId, relationshipId, status: 'PREPARED', sourceBinding: { status: 'ACTIVE' }, targetBinding: { status: 'PREPARED' }, continuityEnvelope: envelope, replayed: false };
    state.handoffs.set(handoffId, { idempotencyKey, requestHash: JSON.stringify(body), response: prepared });
    json(response, prepared, 201);
    return;
  }

  if (request.method === 'POST' && activateHandoffMatch) {
    const relationshipId = decodeURIComponent(activateHandoffMatch[1]);
    const handoffId = decodeURIComponent(activateHandoffMatch[2]);
    const state = continuityFor(scope, relationshipId);
    const handoff = state.handoffs.get(handoffId);
    const body = await readBody(request);
    if (state.stopped) {
      json(response, { code: 'RELATIONSHIP_STOPPED', title: 'Emergency Stop preempted handoff.' }, 409);
      return;
    }
    if (!handoff || body.continuityEnvelope?.integritySignature !== 'fixture-valid-signature') {
      json(response, { code: 'HANDOFF_NOT_FOUND', title: 'The relationship or handoff is unavailable.' }, 404);
      return;
    }
    if (body.targetConversationId === 'timeout') {
      json(response, { code: 'HANDOFF_OUTCOME_UNKNOWN', title: 'Activation is unresolved; the source remains authoritative.' }, 503);
      return;
    }
    if (body.targetConversationId === 'downgrade' || request.headers['x-fixture-tenant'] === 'foreign') {
      json(response, { code: 'HANDOFF_NOT_FOUND', title: 'The relationship or handoff is unavailable.' }, 404);
      return;
    }
    handoff.response = { ...handoff.response, status: 'COMMITTED', targetBinding: { status: 'ACTIVE' }, resolutionEvidenceId: 'evidence-handoff-committed' };
    json(response, handoff.response);
    return;
  }

  if (request.method === 'GET' && evaluationMatch) {
    const relationshipId = decodeURIComponent(evaluationMatch[1]);
    const state = continuityFor(scope, relationshipId);
    json(response, { relationshipId, lifecycleState: state.stopped ? 'STOPPED_EMERGENCY' : relationship(relationshipId).state, interviewState: 'AVAILABLE', context: [], goals: [], skills: [] });
    return;
  }

  if (request.method === 'GET' && contractJourneyMatch) {
    const relationshipId = decodeURIComponent(contractJourneyMatch[1]);
    if (relationshipId !== 'relationship-contract') {
      response.statusCode = 204;
      response.end();
      return;
    }
    json(response, {
      contractId: 'ca57bbd1-62eb-48ab-bd78-2a23053f6551', version: 2, contractHash: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      relationshipState: 'CONTRACT_PENDING_ACCEPTANCE', acceptanceState: 'PENDING', paymentState: 'NOT_STARTED', activationState: 'NOT_STARTED',
      document: {
        professionalDisplayName: 'Digital Marketing Professional', rights: ['Inspect evidence', 'Choose not now without penalty'], obligations: ['Provide accurate context'],
        limitations: ['Cannot publish or spend without authority'], authorityTerms: ['No publishing'], stopTerms: ['Emergency Stop remains available'],
        priceTax: { currency: 'INR', grossAmountInrPaise: 118000, gstAmountInrPaise: 18000, cadence: 'MONTHLY', subscriptionTerms: 'Monthly subscription', adSpendTreatment: 'Ad spend is separate', cancellationAndRefundTerms: 'Cancel before renewal; captured charges follow the stated refund policy' },
      },
    });
    return;
  }

  if (request.method === 'GET' && configurationMatch) {
    const relationshipId = decodeURIComponent(configurationMatch[1]);
    json(response, { sectionType: 'CONFIGURATION', currencyState: 'CURRENT', provenance: { owner: 'BP', sourceProjectionVersion: 'fixture-1', producedAt: '2026-08-12T10:00:00Z' }, availableCommands: [], lifecyclePhase: 'GOAL_VERIFICATION', items: [{ stepKey: 'ONBOARD', label: 'Onboard', state: 'VERIFIED', summary: 'Presentation preferences confirmed.' }, { stepKey: 'INDUCT', label: 'Induct', state: 'VERIFIED', summary: 'Business context confirmed.', continuationTarget: { surface: 'CONVERSATION', relationshipId } }] });
    return;
  }

  if (request.method === 'GET' && goalsMatch) {
    json(response, { sectionType: 'GOALS', currencyState: 'CURRENT', provenance: { owner: 'BP', sourceProjectionVersion: 'fixture-1', producedAt: '2026-08-12T10:00:00Z' }, availableCommands: [], activeGoals: [{ goalId: 'goal-1', goalVersion: '1', skillId: 'CAMPAIGN_PLANNING', skillLabel: 'Campaign planning', measure: 'Qualified enquiries', frequency: 'MONTHLY', verificationStatus: 'PENDING_CUSTOMER', status: 'ACTIVE' }], history: [] });
    return;
  }

  if (request.method === 'GET' && outcomesMatch) {
    json(response, { sectionType: 'BUSINESS_OUTCOMES', currencyState: 'UNAVAILABLE', provenance: { owner: 'BP', sourceProjectionVersion: 'unavailable-1', producedAt: '2026-08-12T10:00:00Z' }, availableCommands: [], items: [] });
    return;
  }

  if (request.method === 'GET' && operationsMatch) {
    json(response, { sectionType: 'OPERATIONS', currencyState: 'CURRENT', provenance: { owner: 'BP', sourceProjectionVersion: 'fixture-1', producedAt: '2026-08-12T10:00:00Z' }, availableCommands: [], eligibilityState: 'LOCKED', requiredGoalIds: ['goal-1'], verifiedGoalIds: [], blockedReasons: ['Customer goal verification is required.'], reassessmentRequired: false });
    return;
  }

  if (request.method === 'GET' && workspaceMatch) {
    const relationshipId = decodeURIComponent(workspaceMatch[1]);
    const family = workspaceMatch[2];
    const lifecycleState = continuityFor(scope, relationshipId).stopped ? 'STOPPED_EMERGENCY' : 'ACTIVE';
    const provenance = { owner: family === 'usage-budget' ? 'WBE' : family === 'work' ? 'PR' : family === 'results' ? 'DMA' : 'BP', sourceProjectionVersion: 'fixture-1', producedAt: '2026-08-10T10:00:00Z' };
    const common = { currencyState: family === 'attention' || family === 'rights-controls' ? 'CURRENT' : 'UNAVAILABLE', provenance, availableCommands: [] };
    const responses = {
      plan: { ...common, sectionType: 'PLAN', planId: '5f33925b-fb0c-4366-8414-7f85309639b9', goals: [] },
      attention: { ...common, sectionType: 'ATTENTION', items: [] },
      work: { ...common, sectionType: 'WORK', items: [] },
      results: { ...common, sectionType: 'RESULTS', outcomes: [] },
      'usage-budget': { ...common, sectionType: 'USAGE_BUDGET', actualAmount: 'Unavailable', forecastRange: 'Unavailable', thresholdState: 'UNAVAILABLE', wbeProjectionVersion: 'unavailable-1' },
      'rights-controls': { ...common, sectionType: 'RIGHTS_CONTROLS', scopeVersion: '1', authorityVersion: '1', lifecycleState, emergencyStopReachable: true },
      evidence: { schemaVersion: '1.0', relationshipId, items: [], authoritativeCursor: `evidence:${relationshipId}:00000001`, hasMore: false },
    };
    json(response, family ? responses[family] : {
      schemaVersion: '1.0', relationshipId, workspaceVersion: 'fixture-1', snapshotState: 'PARTIAL', currencyState: 'CURRENT',
      authoritativeCursor: `workspace:${relationshipId}:00000001`, producedAt: '2026-08-10T10:00:00Z',
      context: { relationshipId, lifecycleState, policySelection: { f4Pol01: 'A', f4Pol02: 'A', f4Pol03: 'B', f4Pol04: 'A', f4Pol05: 'B', f4Pol06: 'A' } }, sections: [],
    });
    return;
  }

  if (request.method === 'GET' && relationshipMatch) {
    const relationshipId = decodeURIComponent(relationshipMatch[1]);
    const state = continuityFor(scope, relationshipId);
    json(response, { ...relationship(relationshipId), state: state.stopped ? 'STOPPED_EMERGENCY' : relationship(relationshipId).state });
    return;
  }
  if (request.method === 'GET' && timelineMatch) {
    json(response, []);
    return;
  }
  if (request.method === 'GET' && messagesMatch) {
    json(response, timeline(scope, decodeURIComponent(messagesMatch[1])));
    return;
  }
  if (request.method === 'POST' && messagesMatch) {
    const relationshipId = decodeURIComponent(messagesMatch[1]);
    const body = await readBody(request);
    if (relationshipId === 'relationship-unknown') {
      json(response, { code: 'CONVERSATION_EXECUTION_UNAVAILABLE', title: 'The send outcome is unknown. Reconnect before retrying.' }, 503);
      return;
    }
    const accepted = message(relationshipId, {
      messageId: body.clientMessageId, actor: 'CUSTOMER', content: body.content, cards: [],
      deliveryState: 'ACCEPTED', processingState: 'QUEUED', evidenceState: 'PENDING', partial: false,
      completionReason: undefined, clientMessageId: body.clientMessageId,
    });
    const currentMessages = messagesFor(scope, relationshipId);
    const existingIndex = currentMessages.findIndex(({ clientMessageId }) => clientMessageId === body.clientMessageId);
    const nextMessages = existingIndex < 0
      ? [...currentMessages, accepted]
      : currentMessages.map((current, index) => index === existingIndex ? accepted : current);
    setMessages(scope, relationshipId, nextMessages);
    json(response, {
      schemaVersion: '1.0', outcome: 'ACCEPTED', message: accepted, executionId,
      authoritativeCursor: `cursor-${relationshipId}-${nextMessages.length}`, replayed: existingIndex >= 0,
    });
    return;
  }
  if (request.method === 'POST' && retryMatch) {
    const relationshipId = decodeURIComponent(retryMatch[1]);
    const existing = messagesFor(scope, relationshipId)[0];
    json(response, { schemaVersion: '1.0', outcome: 'REPLAYED', message: existing, executionId, authoritativeCursor: `cursor-${relationshipId}-1`, replayed: true });
    return;
  }
  if (request.method === 'PUT' && readMatch) {
    json(response, { schemaVersion: '1.0' });
    return;
  }
  if (request.method === 'GET' && streamMatch) {
    const relationshipId = decodeURIComponent(streamMatch[1]);
    response.writeHead(200, { 'Cache-Control': 'no-store', 'Content-Type': 'text/event-stream; charset=utf-8', Connection: 'keep-alive' });
    response.write(`data: ${JSON.stringify(event(relationshipId, 'heartbeat', { data: { serverTime: '2026-08-10T10:01:00.000Z' } }))}\n\n`);
    const clientKey = scopeKey(scope, relationshipId);
    const clients = streamClients.get(clientKey) ?? new Set();
    clients.add(response);
    streamClients.set(clientKey, clients);
    request.on('close', () => clients.delete(response));
    if (relationshipId === 'relationship-stream') {
      setTimeout(() => sendEvent(scope, relationshipId, event(relationshipId, 'response.delta', { executionId, data: { contentIndex: 0, appendText: 'A governed draft update.', partial: true } })), 150);
    }
    return;
  }
  if (request.method === 'DELETE' && cancelMatch) {
    const relationshipId = decodeURIComponent(cancelMatch[1]);
    const current = messagesFor(scope, relationshipId)[0];
    if (current) setMessages(scope, relationshipId, [{ ...current, processingState: 'CANCELLED', partial: true, completionReason: 'CANCELLED' }]);
    json(response, { schemaVersion: '1.0', state: 'CANCELLED', partial: true });
    sendEvent(scope, relationshipId, event(relationshipId, 'stream.cancelled', { executionId }));
    return;
  }
  if (request.method === 'POST' && url.pathname === '/__fixtures/conversations/relationship-evidence/record-evidence') {
    const relationshipId = 'relationship-evidence';
    const current = messagesFor(scope, relationshipId)[0];
    setMessages(scope, relationshipId, [{ ...current, evidenceState: 'RECORDED', evidenceRecordId: 'evidence-confirmed-1' }]);
    json(response, { recorded: true });
    sendEvent(scope, relationshipId, event(relationshipId, 'message.completed', { executionId }));
    return;
  }
  if (request.method === 'POST' && (stopRelationshipMatch || url.pathname === '/api/v1/emergency-stop')) {
    const command = await readBody(request);
    const relationshipId = stopRelationshipMatch ? decodeURIComponent(stopRelationshipMatch[1]) : command.contractId;
    if (relationshipId === 'relationship-stop-unknown') {
      json(response, { code: 'STOP_OUTCOME_UNKNOWN' }, 503);
      return;
    }
    if ('activeSessionIds' in command) {
      json(response, { error: 'INVALID_STOP_SCOPE' }, 422);
      return;
    }
    continuityFor(scope, relationshipId).stopped = true;
    json(response, {
      ...relationship(relationshipId), state: 'STOPPED_EMERGENCY', stateVersion: 3,
      affectedSessions: ['runtime-owned-session'], confirmedAt: '2026-08-10T10:02:00.000Z',
    });
    sendEvent(scope, relationshipId, event(relationshipId, 'stop.applied', { executionId }));
    return;
  }
  json(response, { error: 'NOT_FOUND', path: url.pathname }, 404);
});

server.listen(5001, '0.0.0.0');
process.on('SIGTERM', () => server.close());