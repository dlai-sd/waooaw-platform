// Implements: WC-107 R017-R018 privacy-safe journey telemetry
// Constitutional basis: C-059, C-063

import { SpanStatusCode, trace } from '@opentelemetry/api';

const successfulOutcomes: Record<string, string> = {
  'identity.login': 'LOGIN_COMPLETED',
  'identity.registration': 'REGISTRATION_COMMAND_COMPLETED',
  'identity.logout': 'LOGOUT_COMPLETED',
  'trial.continue': 'TRIAL_STARTED',
  'hire.checkout': 'HIRE_OUTCOME_PRODUCED',
  'my_agents.selection': 'AUTHORIZED_SELECTION_RESOLVED',
};

function statusClass(status: number) {
  return status >= 100 && status <= 599 ? `${Math.floor(status / 100)}xx` : 'unknown';
}

function outcome(operation: string, status: number) {
  if (status >= 200 && status < 400) return successfulOutcomes[operation] ?? 'SUCCEEDED';
  if (status === 409) return 'CONFLICT';
  if ([502, 503, 504].includes(status)) return 'DEPENDENCY_UNAVAILABLE';
  return 'REJECTED';
}

export async function withJourneyTrace(operation: keyof typeof successfulOutcomes, command: () => Promise<Response>) {
  return trace.getTracer('waooaw.web.journeys').startActiveSpan(operation, async (span) => {
    span.setAttribute('waooaw.journey.operation', operation);
    span.setAttribute('waooaw.correlation_id', span.spanContext().traceId);
    try {
      const response = await command();
      span.setAttribute('waooaw.journey.status_class', statusClass(response.status));
      span.setAttribute('waooaw.journey.outcome', outcome(operation, response.status));
      if (response.status >= 500) span.setStatus({ code: SpanStatusCode.ERROR });
      return response;
    } catch (error) {
      span.setAttribute('waooaw.journey.status_class', 'exception');
      span.setAttribute('waooaw.journey.outcome', 'DEPENDENCY_UNAVAILABLE');
      span.setStatus({ code: SpanStatusCode.ERROR });
      throw error;
    } finally {
      span.end();
    }
  });
}
