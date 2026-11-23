// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §7 W4 Telemetry
// Constitutional basis: C-049 (Honest Limitation), C-059 (Implementation Traceability), C-063 (Data Minimisation)

export interface TelemetryRow {
  service: string;
  lines: number;
}

export interface TelemetrySummary {
  source: "console-log" | "none";
  correlation_id: string;
  services: { name: string; lines: number }[];
  note: string;
}

/** Every request the harness makes to the product carries this id, so one run can be found in the service logs. */
export function correlationId(runId: string): string {
  return `acc-${runId.toLowerCase().replace(/[^a-z0-9]/gu, "")}`;
}

/**
 * Console-log correlation read for the run (architecture T6): which services logged the run's correlation id. The nonce
 * comment keeps Log Analytics from serving a cached identical query while the run is polled.
 */
export function buildKql(correlation: string, startIso: string, nonce: string): string {
  if (!/^acc-[a-z0-9]+$/u.test(correlation) || !/^[0-9TZ:.-]+$/u.test(startIso) || !/^[A-Za-z0-9-]+$/u.test(nonce)) {
    throw new Error("telemetry query inputs are not in their safe forms");
  }
  return [
    `// poll ${nonce}`,
    "ContainerAppConsoleLogs_CL",
    `| where TimeGenerated >= datetime(${startIso})`,
    `| where Log_s has "${correlation}"`,
    "| summarize lines = count() by service = ContainerAppName_s",
    "| order by service asc",
  ].join("\n");
}

export function summarizeTelemetry(rows: TelemetryRow[] | undefined, correlation: string): TelemetrySummary {
  if (rows === undefined) {
    return {
      source: "none",
      correlation_id: correlation,
      services: [],
      note: "No telemetry was read: the environment profile has no telemetry workspace, so service reach is NOT-WITNESSED and WC107-R018 stays unproven.",
    };
  }
  const services = rows.map((row) => ({ name: row.service, lines: row.lines })).sort((left, right) => left.name.localeCompare(right.name));
  return {
    source: "console-log",
    correlation_id: correlation,
    services,
    note:
      services.length === 0
        ? "The workspace was read but no service logged the run's correlation id, so no cross-service trace is witnessed and WC107-R018 stays unproven."
        : `${services.length} service(s) logged the run's correlation id; a queryable cross-service trace (OTLP) is still not witnessed, so WC107-R018 stays unproven.`,
  };
}
