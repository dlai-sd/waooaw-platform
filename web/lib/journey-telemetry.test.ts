/** @jest-environment node */

const attributes: Record<string, string> = {};
const span = {
  setAttribute: jest.fn((name: string, value: string) => {
    attributes[name] = value;
  }),
  spanContext: () => ({ traceId: '12'.repeat(16) }),
  setStatus: jest.fn(),
  end: jest.fn(),
};

jest.mock('@opentelemetry/api', () => ({
  SpanStatusCode: { ERROR: 2 },
  trace: {
    getTracer: () => ({
      startActiveSpan: async (_name: string, callback: (activeSpan: typeof span) => Promise<Response>) =>
        callback(span),
    }),
  },
}));

describe('journey telemetry', () => {
  beforeEach(() => {
    for (const key of Object.keys(attributes)) delete attributes[key];
    jest.clearAllMocks();
  });

  it('records only bounded fields and never inspects sensitive response state', async () => {
    const { withJourneyTrace } = await import('./journey-telemetry');
    const sensitive = '77777777-7777-4777-8777-777777777777';

    const response = await withJourneyTrace(
      'trial.continue',
      async () => new Response(JSON.stringify({ relationshipId: sensitive }), { status: 200 })
    );

    expect(response.status).toBe(200);
    expect(attributes).toEqual({
      'waooaw.journey.operation': 'trial.continue',
      'waooaw.correlation_id': '12'.repeat(16),
      'waooaw.journey.status_class': '2xx',
      'waooaw.journey.outcome': 'TRIAL_STARTED',
    });
    expect(JSON.stringify(attributes)).not.toContain(sensitive);
    expect(span.end).toHaveBeenCalledTimes(1);
  });
});