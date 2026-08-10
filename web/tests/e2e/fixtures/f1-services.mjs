import { createServer } from 'node:http';

const primaryRelationshipId = 'relationship-active';
const executionId = '3ead2d21-f908-40b5-9510-b1e77f516d7e';
const streamClients = new Map();
const scopedTimelines = new Map();

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
    state: 'ACTIVE', stateVersion: 2,
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
  const relationshipMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)$/);
  const timelineMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/timeline$/);
  const messagesMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/messages$/);
  const retryMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/messages\/([^/]+)\/retry$/);
  const readMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/read-position$/);
  const streamMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/stream$/);
  const cancelMatch = url.pathname.match(/^\/api\/v1\/employment\/relationships\/([^/]+)\/conversation\/executions\/([^/]+)$/);

  if (request.method === 'GET' && relationshipMatch) {
    json(response, relationship(decodeURIComponent(relationshipMatch[1])));
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
  if (request.method === 'POST' && url.pathname === '/api/v1/emergency-stop') {
    const command = await readBody(request);
    if (command.contractId === 'relationship-stop-unknown') {
      json(response, { code: 'STOP_OUTCOME_UNKNOWN' }, 503);
      return;
    }
    if ('activeSessionIds' in command) {
      json(response, { error: 'INVALID_STOP_SCOPE' }, 422);
      return;
    }
    json(response, { affectedSessions: ['runtime-owned-session'], confirmedAt: '2026-08-10T10:02:00.000Z' });
    sendEvent(scope, command.contractId, event(command.contractId, 'stop.applied', { executionId }));
    return;
  }
  json(response, { error: 'NOT_FOUND', path: url.pathname }, 404);
});

server.listen(5001, '127.0.0.1');
process.on('SIGTERM', () => server.close());