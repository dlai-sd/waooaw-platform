export type WebSessionAssuranceLevel = 'AAL1_CHANNEL' | 'AAL2_ACCOUNT' | 'AAL3_FRESH' | 'AAL4_PAYMENT';

export interface WebManagedSession {
  sessionId: string;
  issuedAt: Date;
  lastSeenAt: Date;
  expiresAt: Date;
  assuranceLevel: WebSessionAssuranceLevel;
  provider: 'GOOGLE' | 'FACEBOOK' | 'APPLE' | 'EMAIL' | 'UNKNOWN';
  deviceLabel: string;
  current: boolean;
}
