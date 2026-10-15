export type ServerSessionMode = 'disabled' | 'shadow' | 'enforced';

export function serverSessionMode(): ServerSessionMode {
  const configured = process.env.WAOOAW_SERVER_SESSION_MODE?.trim().toLowerCase();
  if (configured === 'disabled' || configured === 'shadow' || configured === 'enforced') return configured;
  if (process.env.NODE_ENV === 'test' || process.env.NODE_ENV === 'development') return 'enforced';
  throw new Error('WAOOAW_SERVER_SESSION_MODE must be disabled, shadow, or enforced');
}

export function isApprovedShadowSubject(subject: string): boolean {
  const configured = process.env.WAOOAW_SERVER_SESSION_SHADOW_SUBJECTS;
  if (!configured) return false;
  return configured
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean)
    .includes(subject);
}
