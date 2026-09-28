// Implements: WC-107 R017-R018 privacy-safe distributed tracing
// Constitutional basis: C-059, C-063

export async function register() {
  if (process.env.NEXT_RUNTIME !== 'nodejs' || !process.env.OTEL_EXPORTER_OTLP_ENDPOINT) return;
  const { registerOTel } = await import('@vercel/otel');
  process.env.NEXT_OTEL_FETCH_DISABLED = '1';
  registerOTel({
    serviceName: 'waooaw-web',
    attributes: {
      'service.version': process.env.SERVICE_REVISION ?? 'development',
    },
    instrumentations: [],
    propagators: ['tracecontext'],
  });

  const { context, propagation } = await import('@opentelemetry/api');
  const internalOrigins = new Set(
    [process.env.BUSINESS_PLATFORM_URL, process.env.BILLING_ENGINE_URL, process.env.PROFESSIONAL_RUNTIME_URL]
      .filter((value): value is string => Boolean(value))
      .map((value) => new URL(value).origin)
  );
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (input, init) => {
    const requestUrl = new URL(input instanceof Request ? input.url : input.toString());
    if (!internalOrigins.has(requestUrl.origin)) return originalFetch(input, init);

    const headers = new Headers(input instanceof Request ? input.headers : undefined);
    new Headers(init?.headers).forEach((value, name) => headers.set(name, value));
    propagation.inject(context.active(), headers, {
      set(carrier, name, value) {
        carrier.set(name, value);
      },
    });
    return originalFetch(input, { ...init, headers });
  };
}
