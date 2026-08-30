// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Versioned Event Vocabulary
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { validateAcquisitionEvent } from './acquisition';
const valid = { event_id: '550e8400-e29b-41d4-a716-446655440000', event_name: 'public_page_viewed', schema_version: '1.0', route_id: 'home' };
describe('acquisition event boundary', () => {
  it('accepts a minimal approved event', () => expect(validateAcquisitionEvent(valid).ok).toBe(true));
  it.each(['email', 'tenant_id', 'message', 'raw_referrer'])('rejects prohibited field %s', (field) => expect(validateAcquisitionEvent({ ...valid, [field]: 'private' })).toEqual({ ok: false, error: 'PROHIBITED_FIELD' }));
  it('rejects unsafe attribution', () => expect(validateAcquisitionEvent({ ...valid, utm_source: 'x'.repeat(101) })).toEqual({ ok: false, error: 'INVALID_ATTRIBUTION' }));
});