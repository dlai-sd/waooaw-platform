import 'server-only';

import { randomUUID } from 'node:crypto';
import { databaseErrorDiagnostics } from '@/lib/database-error-diagnostics';

export type DiagnosticDetail = 'standard' | 'stack';
export type DiagnosticContext = Record<string, string | number | boolean | undefined>;

const MAX_TEXT = 2_000;
const MAX_STACK_FRAMES = 20;
const TYPE_NAME = /^[A-Za-z_$][A-Za-z0-9_$]{2,63}$/;
const IDENTIFIER_VALUE = /^[A-Za-z_][A-Za-z0-9_.]{0,126}$/;

// WAOOAW_DIAGNOSTIC_DETAIL=stack adds a redacted message, cause and stack to every failure record.
export function diagnosticDetail(value: string | undefined = process.env.WAOOAW_DIAGNOSTIC_DETAIL): DiagnosticDetail {
  return value === 'stack' ? 'stack' : 'standard';
}

// Removes values that can carry credentials or personal data while keeping SQL identifiers,
// error wording and stack frames readable.
export function redactDiagnosticText(text: string): string {
  return text
    .replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*/g, '[jwt]')
    .replace(/\b(Bearer|Basic)\s+[^\s,;]+/gi, '$1 [redacted]')
    .replace(/\b([a-z][a-z0-9+.-]*:\/\/)[^\s/@"'<>]+@/gi, '$1[credentials]@')
    .replace(/(\b[a-z][a-z0-9+.-]*:\/\/[^\s?#"'<>]*)\?[^\s#"'<>]*/gi, '$1?[redacted]')
    .replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, '[email]')
    .replace(
      /\b(password|passwd|pwd|secret|token|cookie|authorization|api[_-]?key|client[_-]?secret|code|state|nonce|verifier)(\s*[=:]\s*)("[^"]*"|'[^']*'|[^\s,;&)]+)/gi,
      '$1$2[redacted]'
    )
    .replace(/"([^"\n]{0,512})"/g, (match, value: string) => (IDENTIFIER_VALUE.test(value) ? match : '"[value]"'))
    .replace(/'([^'\n]{0,512})'/g, (match, value: string) => (IDENTIFIER_VALUE.test(value) ? match : "'[value]'"))
    .replace(/\b[A-Za-z0-9+_=-]{32,}\b/g, '[opaque]')
    .slice(0, MAX_TEXT);
}

function errorType(error: unknown): string {
  if (error === undefined) return 'none';
  if (!error || typeof error !== 'object') return typeof error;
  const named = (error as { name?: unknown }).name;
  if (typeof named === 'string' && TYPE_NAME.test(named) && named !== 'Error') return named;
  const constructorName = (error as { constructor?: { name?: unknown } }).constructor?.name;
  if (typeof constructorName === 'string' && TYPE_NAME.test(constructorName)) return constructorName;
  return typeof named === 'string' && TYPE_NAME.test(named) ? named : 'UnidentifiedError';
}

function stackFrames(error: object): string | undefined {
  const stack = (error as { stack?: unknown }).stack;
  if (typeof stack !== 'string') return undefined;
  const frames = stack
    .split('\n')
    .filter((line) => /^\s*at\s/.test(line))
    .slice(0, MAX_STACK_FRAMES)
    .map((line) => line.trim());
  return frames.length > 0 ? redactDiagnosticText(frames.join('\n')) : undefined;
}

function failureFields(error: unknown, detail: DiagnosticDetail, prefix = ''): Record<string, string> {
  const fields: Record<string, string> = { [`${prefix}errorType`]: errorType(error) };
  if (!error || typeof error !== 'object') return fields;
  const database = databaseErrorDiagnostics(error);
  for (const [key, value] of Object.entries(database)) {
    if (key !== 'errorClass' && typeof value === 'string') fields[`${prefix}${key}`] = value;
  }
  if (database.errorClass === 'database') fields[`${prefix}errorClass`] = 'database';
  if (detail === 'stack') {
    const message = (error as { message?: unknown }).message;
    if (typeof message === 'string' && message) fields[`${prefix}message`] = redactDiagnosticText(message);
    const frames = stackFrames(error);
    if (frames) fields[`${prefix}stack`] = frames;
  }
  return fields;
}

function safeContext(context: DiagnosticContext): Record<string, string | number | boolean> {
  const safe: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(context)) {
    if (value === undefined) continue;
    safe[key] = typeof value === 'string' ? redactDiagnosticText(value).slice(0, 200) : value;
  }
  return safe;
}

/**
 * Emits one single-line JSON record (Log Analytics keeps it as one row) and returns its
 * correlation ID. Never pass tokens, cookies, transaction payloads or user input as context.
 */
export function logServerFailure(
  event: string,
  error?: unknown,
  context: DiagnosticContext = {},
  level: 'error' | 'warn' = 'error'
): string {
  const correlationId =
    typeof context.correlationId === 'string' && /^[A-Za-z0-9-]{1,64}$/.test(context.correlationId)
      ? context.correlationId
      : randomUUID();
  const detail = diagnosticDetail();
  const record: Record<string, unknown> = {
    level,
    event,
    ...safeContext(context),
    correlationId,
    ...failureFields(error, detail),
  };
  const cause = error && typeof error === 'object' ? (error as { cause?: unknown }).cause : undefined;
  if (cause !== undefined) Object.assign(record, failureFields(cause, detail, 'cause.'));
  const line = JSON.stringify(record);
  if (level === 'warn') console.warn(line);
  else console.error(line);
  return correlationId;
}
