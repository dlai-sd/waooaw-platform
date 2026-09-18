import { beginAuthTransition, recordAuthTransition } from './auth-transition';

describe('auth transition diagnostics', () => {
  beforeEach(() => sessionStorage.clear());

  it('emits only bounded transition fields and clears state after resolution', () => {
    const records: unknown[] = [];
    window.addEventListener('waooaw:auth-transition', (event) => records.push((event as CustomEvent).detail));

    const correlationId = beginAuthTransition();
    recordAuthTransition('BROKER_REDIRECT_REQUESTED', 'OK');
    recordAuthTransition('SESSION_RESOLVED', 'OK');

    expect(correlationId).toMatch(/^[0-9a-f-]{36}$/);
    expect(records).toHaveLength(3);
    expect(records).toEqual(expect.arrayContaining([
      expect.objectContaining({ correlationId, stage: 'ROUTE_REQUESTED', reasonCode: 'OK' }),
      expect.objectContaining({ correlationId, stage: 'BROKER_REDIRECT_REQUESTED', reasonCode: 'OK' }),
      expect.objectContaining({ correlationId, stage: 'SESSION_RESOLVED', reasonCode: 'OK' }),
    ]));
    expect(Object.keys(records[0] as object).sort()).toEqual(['correlationId', 'durationMs', 'reasonCode', 'stage']);
    expect(sessionStorage.getItem('waooaw:auth-transition')).toBeNull();
  });
});