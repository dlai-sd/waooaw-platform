export type AcquisitionIntentCommand = {
  professionalType: string;
  professionalVersion: string;
  intent: 'TRIAL' | 'HIRE';
  disclosureRevision: string;
  termsVersion: string;
  acceptance: 'ACCEPT_EMPLOYMENT_CONTRACT';
  couponCode?: string;
};

export async function persistAcquisitionIntent(
  accessToken: string,
  idempotencyKey: string,
  command: AcquisitionIntentCommand
): Promise<Response> {
  return fetch(`${process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001'}/api/v1/acquisition/intents`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify(command),
    cache: 'no-store',
  });
}
