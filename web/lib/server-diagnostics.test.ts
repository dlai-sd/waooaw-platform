/** @jest-environment node */

import { diagnosticDetail, logServerFailure, redactDiagnosticText } from '@/lib/server-diagnostics';

// Assembled at runtime so secret scanners do not treat the synthetic fixture as a credential.
const jwt = ['eyJhbGciOiJSUzI1NiJ9', 'eyJzdWIiOiJ1c2VyIn0', 'c2lnbmF0dXJl'].join('.');
const opaque = 'Zm9vYmFyYmF6cXV4cXV1eHF1dXhxdXV4cXV1eHF1dXg';

describe('server diagnostics', () => {
  afterEach(() => {
    Reflect.deleteProperty(process.env, 'WAOOAW_DIAGNOSTIC_DETAIL');
    jest.restoreAllMocks();
  });

  it('defaults to standard detail and accepts only stack as the alternative', () => {
    expect(diagnosticDetail(undefined)).toBe('standard');
    expect(diagnosticDetail('verbose')).toBe('standard');
    expect(diagnosticDetail('stack')).toBe('stack');
  });

  it('redacts credentials, personal data and opaque values but keeps identifiers', () => {
    const redacted = redactDiagnosticText(
      [
        `token ${jwt}`,
        'Authorization: Bearer abc.def',
        'postgres://web_session:p4ss@db.internal:5432/waooaw?sslmode=require',
        'https://idp.example/callback?code=abc&state=xyz',
        'user person@example.com',
        'client_secret=s3cr3t password="hunter 2"',
        `opaque ${opaque}`,
        'relation "web_session.oidc_transactions" value \'Jane Doe\'',
      ].join('\n')
    );
    for (const secret of [
      jwt,
      'abc.def',
      'p4ss',
      'sslmode',
      'code=abc',
      'person@example.com',
      's3cr3t',
      'hunter',
      opaque,
      'Jane',
    ])
      expect(redacted).not.toContain(secret);
    expect(redacted).toContain('"web_session.oidc_transactions"');
    expect(redacted).toContain('postgres://[credentials]@db.internal:5432/waooaw?[redacted]');
  });

  it('emits one standard-mode JSON line with the real type, database fields and no message', () => {
    class PostgresError extends Error {}
    const failure = Object.assign(new PostgresError(`denied for ${jwt}`), {
      code: '42501',
      schema_name: 'web_session',
      table_name: 'oidc_transactions',
    });
    const logged = jest.spyOn(console, 'error').mockImplementation(() => undefined);

    const correlationId = logServerFailure('identity.test', failure, { provider: 'GOOGLE' });

    const line = String(logged.mock.calls[0][0]);
    expect(line).not.toContain('\n');
    expect(JSON.parse(line)).toEqual({
      level: 'error',
      event: 'identity.test',
      provider: 'GOOGLE',
      correlationId,
      errorType: 'PostgresError',
      errorClass: 'database',
      code: '42501',
      schema: 'web_session',
      table: 'oidc_transactions',
    });
  });

  it('adds redacted message, stack and cause in stack mode', () => {
    process.env.WAOOAW_DIAGNOSTIC_DETAIL = 'stack';
    const failure = new Error(`token rejected ${jwt}`, { cause: new TypeError('password=abc missing') });
    const logged = jest.spyOn(console, 'warn').mockImplementation(() => undefined);

    logServerFailure('identity.test', failure, {}, 'warn');

    const line = String(logged.mock.calls[0][0]);
    const record = JSON.parse(line) as Record<string, string>;
    expect(record.message).toBe('token rejected [jwt]');
    expect(record.stack).toMatch(/^at .*server-diagnostics\.test/);
    expect(record['cause.errorType']).toBe('TypeError');
    expect(record['cause.message']).toBe('password=[redacted] missing');
    expect(line).not.toContain(jwt);
    expect(line).not.toContain('abc');
  });
});
