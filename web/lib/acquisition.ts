// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Versioned Event Vocabulary
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)

const eventFields = {
  public_page_viewed: ['route_id', 'content_id'],
  professional_viewed: ['professional_type'],
  registration_started: ['entry_route', 'professional_type'],
  identity_provider_selected: ['provider_id'],
  registration_completed: [],
  hire_journey_started: ['professional_type', 'entry_route'],
  contact_invoked: ['contact_intent'],
  consent_updated: ['analytics', 'advertising'],
} as const;

const commonFields = ['event_id', 'event_name', 'schema_version', 'timestamp', 'route_id', 'locale', 'consent', 'utm_source', 'utm_medium', 'utm_campaign', 'referrer_class', 'deduplication_id'] as const;
const boundedValue = /^[\p{L}\p{N} ._/-]{1,100}$/u;

export type AcquisitionValidation = { ok: true; event: Record<string, unknown> } | { ok: false; error: string };

export function validateAcquisitionEvent(input: unknown): AcquisitionValidation {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return { ok: false, error: 'INVALID_EVENT' };
  const event = input as Record<string, unknown>;
  const eventName = event.event_name;
  if (typeof eventName !== 'string' || !(eventName in eventFields)) return { ok: false, error: 'UNKNOWN_EVENT' };
  const allowed = new Set<string>([...commonFields, ...eventFields[eventName as keyof typeof eventFields]]);
  if (Object.keys(event).some((key) => !allowed.has(key))) return { ok: false, error: 'PROHIBITED_FIELD' };
  if (event.schema_version !== '1.0' || typeof event.event_id !== 'string' || !/^[0-9a-f-]{36}$/i.test(event.event_id)) return { ok: false, error: 'INVALID_ENVELOPE' };
  for (const key of ['utm_source', 'utm_medium', 'utm_campaign']) {
    if (event[key] !== undefined && (typeof event[key] !== 'string' || !boundedValue.test(event[key] as string))) return { ok: false, error: 'INVALID_ATTRIBUTION' };
  }
  return { ok: true, event: Object.fromEntries(Object.entries(event).filter(([key]) => allowed.has(key))) };
}