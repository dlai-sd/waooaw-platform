import { isApprovedShadowSubject, serverSessionMode } from '@/lib/server-session-mode';

describe('server session migration mode', () => {
  const originalMode = process.env.WAOOAW_SERVER_SESSION_MODE;
  const originalSubjects = process.env.WAOOAW_SERVER_SESSION_SHADOW_SUBJECTS;

  afterEach(() => {
    if (originalMode === undefined) Reflect.deleteProperty(process.env, 'WAOOAW_SERVER_SESSION_MODE');
    else process.env.WAOOAW_SERVER_SESSION_MODE = originalMode;
    if (originalSubjects === undefined) Reflect.deleteProperty(process.env, 'WAOOAW_SERVER_SESSION_SHADOW_SUBJECTS');
    else process.env.WAOOAW_SERVER_SESSION_SHADOW_SUBJECTS = originalSubjects;
  });

  it.each(['disabled', 'shadow', 'enforced'] as const)('accepts the %s migration state', (mode) => {
    process.env.WAOOAW_SERVER_SESSION_MODE = mode;
    expect(serverSessionMode()).toBe(mode);
  });

  it('restricts shadow comparison to explicitly approved subjects', () => {
    process.env.WAOOAW_SERVER_SESSION_SHADOW_SUBJECTS = 'approved-subject, second-subject';

    expect(isApprovedShadowSubject('approved-subject')).toBe(true);
    expect(isApprovedShadowSubject('customer-subject')).toBe(false);
  });
});
