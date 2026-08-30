// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Versioned Event Vocabulary
// Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-063 (Data Minimisation)

const eventFields = {
  public_page_viewed: { required: [], optional: ['content_id'] },
  professional_viewed: { required: ['professional_type'], optional: [] },
  registration_started: { required: ['entry_route'], optional: ['professional_type'] },
  identity_provider_selected: { required: ['provider_id'], optional: [] },
  registration_completed: { required: [], optional: [] },
  hire_journey_started: { required: ['professional_type', 'entry_route'], optional: [] },
  contact_invoked: { required: ['contact_intent'], optional: [] },
  consent_updated: { required: ['analytics', 'advertising'], optional: [] },
} as const;

const commonFields = ['event_id', 'event_name', 'schema_version', 'timestamp', 'route_id', 'locale', 'environment', 'consent', 'utm_source', 'utm_medium', 'utm_campaign', 'referrer_class', 'deduplication_id'] as const;
const boundedValue = /^[\p{L}\p{N} ._/-]{1,100}$/u;
const eventId = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const locales = new Set(['en', 'hi', 'mr', 'ta', 'te', 'kn', 'gu', 'bn', 'ml', 'pa', 'ur']);
const environments = new Set(['demo', 'uat', 'production']);
const referrerClasses = new Set(['direct', 'search', 'social', 'campaign', 'other']);

export type AcquisitionValidation = { ok: true; event: Record<string, unknown> } | { ok: false; error: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export function validateAcquisitionEvent(input: unknown): AcquisitionValidation {
  if (!isRecord(input)) return { ok: false, error: 'INVALID_EVENT' };
  const event = input;
  const eventName = event.event_name;
  if (typeof eventName !== 'string' || !(eventName in eventFields)) return { ok: false, error: 'UNKNOWN_EVENT' };
  const fields = eventFields[eventName as keyof typeof eventFields];
  const allowed = new Set<string>([...commonFields, ...fields.required, ...fields.optional]);
  if (Object.keys(event).some((key) => !allowed.has(key))) return { ok: false, error: 'PROHIBITED_FIELD' };
  if (
    event.schema_version !== '1.0'
    || typeof event.event_id !== 'string' || !eventId.test(event.event_id)
    || typeof event.deduplication_id !== 'string' || !eventId.test(event.deduplication_id)
    || typeof event.timestamp !== 'string' || Number.isNaN(Date.parse(event.timestamp))
    || typeof event.route_id !== 'string' || !boundedValue.test(event.route_id)
    || typeof event.locale !== 'string' || !locales.has(event.locale)
    || typeof event.environment !== 'string' || !environments.has(event.environment)
    || !isRecord(event.consent)
    || Object.keys(event.consent).some((key) => key !== 'analytics' && key !== 'advertising')
    || typeof event.consent.analytics !== 'boolean'
    || typeof event.consent.advertising !== 'boolean'
  ) return { ok: false, error: 'INVALID_ENVELOPE' };
  if (fields.required.some((key) => event[key] === undefined)) return { ok: false, error: 'MISSING_EVENT_DATA' };
  for (const key of [...fields.required, ...fields.optional]) {
    if (event[key] !== undefined && (typeof event[key] !== 'string' || !boundedValue.test(event[key] as string))) {
      if (eventName !== 'consent_updated' || (key !== 'analytics' && key !== 'advertising') || typeof event[key] !== 'boolean') return { ok: false, error: 'INVALID_EVENT_DATA' };
    }
  }
  for (const key of ['utm_source', 'utm_medium', 'utm_campaign']) {
    if (event[key] !== undefined && (typeof event[key] !== 'string' || !boundedValue.test(event[key] as string))) return { ok: false, error: 'INVALID_ATTRIBUTION' };
  }
  if (event.referrer_class !== undefined && (typeof event.referrer_class !== 'string' || !referrerClasses.has(event.referrer_class))) return { ok: false, error: 'INVALID_ATTRIBUTION' };
  return { ok: true, event: Object.fromEntries(Object.entries(event).filter(([key]) => allowed.has(key))) };
}