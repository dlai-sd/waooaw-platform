// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §4 Run Lifecycle step 3
// Constitutional basis: C-059 (Implementation Traceability), C-049 (Honest Limitation)

export interface ProbeTarget {
  name: string;
  url: string;
}

export interface ProbeResult {
  name: string;
  ready: boolean;
  detail: string;
}

export interface ProbeOutcome {
  available: boolean;
  results: ProbeResult[];
}

type FetchLike = (url: string, init: { signal: AbortSignal; redirect: "manual" }) => Promise<{ status: number }>;

/** A stopped or unreachable environment is a result (ENV-UNAVAILABLE), never a step failure (ADR-054 item 12). */
export async function probeEnvironment(
  targets: ProbeTarget[],
  options: { timeoutMs: number; fetchImpl?: FetchLike },
): Promise<ProbeOutcome> {
  const fetchImpl: FetchLike = options.fetchImpl ?? ((url, init) => fetch(url, init));
  const results = await Promise.all(
    targets.map(async (target): Promise<ProbeResult> => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), options.timeoutMs);
      try {
        const response = await fetchImpl(target.url, { signal: controller.signal, redirect: "manual" });
        const ready = response.status >= 200 && response.status < 400;
        return { name: target.name, ready, detail: `HTTP ${response.status}` };
      } catch (error) {
        const reason = controller.signal.aborted ? `no answer within ${options.timeoutMs} ms` : String(error);
        return { name: target.name, ready: false, detail: reason };
      } finally {
        clearTimeout(timer);
      }
    }),
  );
  return { available: results.every((result) => result.ready), results };
}
