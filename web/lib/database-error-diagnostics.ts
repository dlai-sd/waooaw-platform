export type DatabaseErrorDiagnostics = {
  errorClass: 'database' | 'application';
  code?: string;
  severity?: string;
  schema?: string;
  table?: string;
  constraint?: string;
  routine?: string;
};

const CODE = /^[A-Z0-9_]{2,40}$/;
const SEVERITY = /^(ERROR|FATAL|PANIC|WARNING)$/;
const IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_]{0,62}$/;

function field(source: Record<string, unknown>, name: string, pattern: RegExp): string | undefined {
  const value = source[name];
  return typeof value === 'string' && pattern.test(value) ? value : undefined;
}

// Messages, details, hints, queries and parameters can echo credentials or row values, so only
// allow-listed SQLSTATE/driver codes and catalog identifiers are ever emitted.
export function databaseErrorDiagnostics(error: unknown): DatabaseErrorDiagnostics {
  if (!error || typeof error !== 'object') return { errorClass: 'application' };
  const source = error as Record<string, unknown>;
  const code = field(source, 'code', CODE);
  if (!code) return { errorClass: 'application' };
  const diagnostics: DatabaseErrorDiagnostics = { errorClass: 'database', code };
  const severity = field(source, 'severity_local', SEVERITY) ?? field(source, 'severity', SEVERITY);
  const schema = field(source, 'schema_name', IDENTIFIER);
  const table = field(source, 'table_name', IDENTIFIER);
  const constraint = field(source, 'constraint_name', IDENTIFIER);
  const routine = field(source, 'routine', IDENTIFIER);
  if (severity) diagnostics.severity = severity;
  if (schema) diagnostics.schema = schema;
  if (table) diagnostics.table = table;
  if (constraint) diagnostics.constraint = constraint;
  if (routine) diagnostics.routine = routine;
  return diagnostics;
}
