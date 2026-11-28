"""Lint the PostgreSQL init chain for the WC-124 idempotent authoring standard.

Every file under ``infrastructure/postgres/init`` is re-applied by the Demo
provisioner whenever its digest changes, so every top-level statement must be
safe to run against a database that already contains its effect. This lint is
the executable form of the Platform IT Expert SQL authoring standard: it fails
on any statement that would error on a second run.

Rules (statement level, after comments/strings/dollar-quotes are honoured):

* ``CREATE SCHEMA|TABLE|INDEX|UNIQUE INDEX|SEQUENCE|EXTENSION|MATERIALIZED VIEW``
  must carry ``IF NOT EXISTS``.
* ``CREATE FUNCTION|PROCEDURE|VIEW|RULE|TRIGGER`` must be ``CREATE OR REPLACE``.
* ``CREATE CONSTRAINT TRIGGER`` and ``CREATE POLICY`` must be preceded by a
  matching ``DROP ... IF EXISTS`` statement in the same file.
* ``CREATE TYPE|DOMAIN|ROLE|USER`` and ``ALTER TABLE ... ADD CONSTRAINT`` must be
  wrapped in a ``DO`` block existence guard (an ``ADD CONSTRAINT`` paired with
  ``DROP CONSTRAINT IF EXISTS`` of the same name in one statement is accepted).
* ``ALTER TABLE ... ADD COLUMN`` must use ``ADD COLUMN IF NOT EXISTS``;
  ``DROP CONSTRAINT`` must use ``DROP CONSTRAINT IF EXISTS``.
* Top-level ``INSERT`` must end with ``ON CONFLICT`` or be wrapped in a ``DO``
  existence guard.
* Dynamic ``EXECUTE format('CREATE POLICY|TRIGGER ...')`` inside ``DO`` blocks
  must be preceded by a matching ``EXECUTE format('DROP ... IF EXISTS ...')`` or
  an ``IF NOT EXISTS (SELECT 1 FROM pg_policy|pg_trigger ...)`` guard.
* Shell (``*.sh``) init files are not applied by the Demo provisioner and are
  reported as informational.
* A file whose first line is ``-- wc177-apply: update`` is also checked against the update-class
  rules (``update_rule_findings``); a file without the header is ``full`` class and is unaffected.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import asdict, dataclass

DEFAULT_INIT_DIRECTORY = pathlib.Path("infrastructure/postgres/init")

IF_NOT_EXISTS_OBJECTS = (
    "SCHEMA",
    "TABLE",
    "UNIQUE INDEX",
    "INDEX",
    "SEQUENCE",
    "EXTENSION",
    "MATERIALIZED VIEW",
)
OR_REPLACE_OBJECTS = ("FUNCTION", "PROCEDURE", "VIEW", "RULE", "TRIGGER")
DO_GUARDED_OBJECTS = ("TYPE", "DOMAIN", "ROLE", "USER")
APPLY_HEADER = re.compile(r"^-- wc177-apply: (update|full)\s*$")
UPDATE_OWNERS = ("bp_owner", "wbe_owner")
OTHER_OWNERS = (
    "ce_owner",
    "pr_owner",
    "air_owner",
    "billing_owner",
    "web_session_owner",
    "keycloak_owner",
    "temporal_owner",
)
OTHER_OWNER_PATTERN = re.compile(r"\b(" + "|".join(OTHER_OWNERS) + r")\b", re.I)


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule: str
    statement: str


def split_statements(text: str) -> list[tuple[int, str]]:
    """Return ``(line_number, statement)`` chunks honouring comments, strings and dollar quotes."""
    out: list[tuple[int, str]] = []
    i = 0
    n = len(text)
    start = 0
    state: str | None = None
    dollar = ""
    while i < n:
        ch = text[i]
        if state is None:
            if text.startswith("--", i):
                state = "line"
                i += 2
                continue
            if text.startswith("/*", i):
                state = "block"
                i += 2
                continue
            if ch == "'":
                state = "str"
                i += 1
                continue
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", text[i:])
            if match:
                dollar = match.group(0)
                state = "dollar"
                i += len(dollar)
                continue
            if ch == ";":
                out.append((text.count("\n", 0, start) + 1, text[start:i]))
                start = i + 1
            i += 1
        elif state == "line":
            if ch == "\n":
                state = None
            i += 1
        elif state == "block":
            if text.startswith("*/", i):
                state = None
                i += 2
            else:
                i += 1
        elif state == "str":
            if ch == "'":
                if i + 1 < n and text[i + 1] == "'":
                    i += 2
                    continue
                state = None
            i += 1
        elif state == "dollar":
            if text.startswith(dollar, i):
                state = None
                i += len(dollar)
            else:
                i += 1
    out.append((text.count("\n", 0, start) + 1, text[start:]))
    return out


def strip_comments(statement: str) -> str:
    """Remove SQL comments outside strings/dollar quotes so keyword checks see only code."""
    out: list[str] = []
    i = 0
    n = len(statement)
    state: str | None = None
    dollar = ""
    while i < n:
        ch = statement[i]
        if state is None:
            if statement.startswith("--", i):
                j = statement.find("\n", i)
                i = n if j < 0 else j
                continue
            if statement.startswith("/*", i):
                j = statement.find("*/", i)
                i = n if j < 0 else j + 2
                continue
            if ch == "'":
                state = "str"
            else:
                match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", statement[i:])
                if match:
                    dollar = match.group(0)
                    state = "dollar"
                    out.append(dollar)
                    i += len(dollar)
                    continue
            out.append(ch)
            i += 1
        elif state == "str":
            out.append(ch)
            if ch == "'":
                if i + 1 < n and statement[i + 1] == "'":
                    out.append("'")
                    i += 2
                    continue
                state = None
            i += 1
        else:
            if statement.startswith(dollar, i):
                state = None
                out.append(dollar)
                i += len(dollar)
            else:
                out.append(ch)
                i += 1
    return "".join(out).strip()


def _lead(code: str) -> str:
    """Return the leading statement words (upper-cased) used for rule dispatch."""
    return re.sub(r"\s+", " ", code[:160]).upper()


def _drop_statements(statements: list[tuple[int, str]]) -> set[tuple[str, str, str]]:
    drops: set[tuple[str, str, str]] = set()
    for _, raw in statements:
        code = strip_comments(raw)
        match = re.match(
            r"DROP\s+(POLICY|TRIGGER)\s+IF\s+EXISTS\s+([\w\"]+)\s+ON\s+([\w\".]+)",
            code,
            re.I,
        )
        if match:
            kind, name, table = match.groups()
            drops.add((kind.upper(), name.strip('"').lower(), table.strip('"').lower()))
    return drops


def _check_do_block(code: str) -> list[str]:
    """Return rule ids violated by dynamic DDL inside a DO block."""
    violations: list[str] = []
    for kind in ("POLICY", "TRIGGER"):
        creates = re.findall(rf"EXECUTE\s+format\s*\(\s*'CREATE\s+{kind}\b", code, re.I)
        drops = re.findall(rf"EXECUTE\s+format\s*\(\s*'DROP\s+{kind}\s+IF\s+EXISTS\b", code, re.I)
        catalog = "pg_policy" if kind == "POLICY" else "pg_trigger"
        guards = re.findall(rf"IF\s+NOT\s+EXISTS\s*\(\s*SELECT\s+1\s+FROM\s+{catalog}\b", code, re.I)
        if len(creates) > len(drops) + len(guards):
            violations.append(f"dynamic-{kind.lower()}-without-drop")
    return violations


def declared_class(text: str) -> str:
    """``update`` only when the first non-blank line is the update header; anything else is ``full``."""
    for line in text.splitlines():
        if line.strip():
            match = APPLY_HEADER.match(line)
            return match.group(1) if match else "full"
    return "full"


def update_rule_findings(file_name: str, text: str) -> list[Finding]:
    """Rules an ``-- wc177-apply: update`` file must follow (WC-177 Design, file classes).

    The update job wraps each file and its ledger row in one transaction as a login role that holds
    ``bp_owner`` and ``wbe_owner`` without a default role, so every statement runs after
    ``SET LOCAL ROLE`` to one of those owners and nothing destructive or privileged is allowed.
    """
    findings: list[Finding] = []

    def add(line: int, rule: str, code: str) -> None:
        findings.append(Finding(file_name, line, rule, re.sub(r"\s+", " ", code[:120])))

    for number, line_text in enumerate(text.splitlines(), 1):
        if line_text.lstrip().startswith("\\"):
            add(number, "psql-meta-command", line_text)
    role: str | None = None
    lock_timeout = statement_timeout = False
    for line, raw in split_statements(text):
        code = strip_comments(raw)
        if not code:
            continue
        flat = re.sub(r"\s+", " ", code)
        if re.match(r"(BEGIN|COMMIT|END|ROLLBACK|ABORT|START TRANSACTION|SAVEPOINT|RELEASE|PREPARE TRANSACTION)\b", flat, re.I):
            add(line, "transaction-control", code)
            continue
        set_role = re.match(r"SET\s+LOCAL\s+ROLE\s+\"?(\w+)\"?", flat, re.I)
        if set_role:
            role = set_role.group(1).lower()
            if role not in UPDATE_OWNERS:
                add(line, "set-role-outside-update-owners", code)
            continue
        if re.match(r"SET\s+(SESSION\s+)?ROLE\b", flat, re.I):
            add(line, "set-role-without-local", code)
            continue
        if re.match(r"RESET\s+ROLE\b", flat, re.I):
            role = None
            continue
        if re.match(r"SET\s+LOCAL\s+lock_timeout\b", flat, re.I):
            lock_timeout = True
            continue
        if re.match(r"SET\s+LOCAL\s+statement_timeout\b", flat, re.I):
            statement_timeout = True
            continue
        if re.match(r"(SET|SHOW|SELECT)\b", flat, re.I):
            if OTHER_OWNER_PATTERN.search(flat):
                add(line, "other-owner-referenced", code)
            continue
        if role is None:
            add(line, "statement-without-set-local-role", code)
        if not (lock_timeout and statement_timeout):
            add(line, "missing-lock-or-statement-timeout", code)
        if OTHER_OWNER_PATTERN.search(flat):
            add(line, "other-owner-referenced", code)
        if re.match(r"DROP\b", flat, re.I) and not re.match(r"DROP\s+(POLICY|TRIGGER)\s+IF\s+EXISTS\b", flat, re.I):
            add(line, "drop-not-allowed", code)
        if re.match(r"(TRUNCATE|DELETE)\b", flat, re.I):
            add(line, "truncate-or-delete-not-allowed", code)
        if re.match(r"ALTER\b", flat, re.I) and re.search(r"\bRENAME\b", flat, re.I):
            add(line, "rename-not-allowed", code)
        if re.match(r"ALTER\s+TABLE\b", flat, re.I):
            if re.search(r"\bALTER\s+COLUMN\s+\S+\s+(SET\s+DATA\s+)?TYPE\b", flat, re.I):
                add(line, "column-type-change-not-allowed", code)
            if re.search(r"\bDROP\s+COLUMN\b", flat, re.I):
                add(line, "drop-not-allowed", code)
            for column in re.split(r"\bADD\s+COLUMN\b", flat, flags=re.I)[1:]:
                clause = re.split(r"\s*,\s*(?=ADD|DROP|ALTER|OWNER|ENABLE|FORCE)", column, maxsplit=1, flags=re.I)[0]
                if re.search(r"\bNOT\s+NULL\b", clause, re.I) and not re.search(r"\bDEFAULT\b", clause, re.I):
                    add(line, "not-null-column-without-default", code)
        if re.match(r"(CREATE|ALTER|DROP)\s+(ROLE|USER|GROUP)\b", flat, re.I):
            add(line, "role-change-not-allowed", code)
        if re.match(r"(GRANT|REVOKE)\b", flat, re.I) and not re.search(r"\bON\b", flat, re.I):
            add(line, "role-membership-not-allowed", code)
        if re.match(r"(CREATE|ALTER|DROP)\s+EXTENSION\b", flat, re.I):
            add(line, "extension-not-allowed", code)
        if re.match(
            r"(ALTER\s+SYSTEM|COPY|CREATE\s+DATABASE|ALTER\s+DATABASE|REINDEX|VACUUM|CLUSTER|REASSIGN|LOCK)\b", flat, re.I
        ):
            add(line, "statement-not-allowed", code)
        for owner in re.findall(r"\b(?:OWNER\s+TO|AUTHORIZATION|FOR\s+ROLE)\s+\"?(\w+)\"?", flat, re.I):
            if owner.lower() not in UPDATE_OWNERS:
                add(line, "owner-outside-update-owners", code)
        if re.match(r"UPDATE\b", flat, re.I) and not re.search(r"\bWHERE\b", flat, re.I):
            add(line, "unbounded-update", code)
    return findings


def lint_sql(file_name: str, text: str) -> list[Finding]:
    statements = split_statements(text)
    drops = _drop_statements(statements)
    findings: list[Finding] = []

    def add(line: int, rule: str, code: str) -> None:
        findings.append(Finding(file_name, line, rule, re.sub(r"\s+", " ", code[:120])))

    for line, raw in statements:
        code = strip_comments(raw)
        if not code:
            continue
        lead = _lead(code)
        if lead.startswith("DO "):
            for rule in _check_do_block(code):
                add(line, rule, code)
            continue
        if lead.startswith("CREATE "):
            if re.match(r"CREATE\s+CONSTRAINT\s+TRIGGER\s+([\w\"]+)\s+.*?\bON\s+([\w\".]+)", code, re.I | re.S):
                match = re.match(r"CREATE\s+CONSTRAINT\s+TRIGGER\s+([\w\"]+)\s+.*?\bON\s+([\w\".]+)", code, re.I | re.S)
                key = ("TRIGGER", match.group(1).strip('"').lower(), match.group(2).strip('"').lower())
                if key not in drops:
                    add(line, "constraint-trigger-without-drop", code)
                continue
            if re.match(r"CREATE\s+POLICY\s+([\w\"]+)\s+ON\s+([\w\".]+)", code, re.I):
                match = re.match(r"CREATE\s+POLICY\s+([\w\"]+)\s+ON\s+([\w\".]+)", code, re.I)
                key = ("POLICY", match.group(1).strip('"').lower(), match.group(2).strip('"').lower())
                if key not in drops:
                    add(line, "policy-without-drop", code)
                continue
            if re.match(r"CREATE\s+(OR\s+REPLACE\s+)?(" + "|".join(OR_REPLACE_OBJECTS) + r")\b", lead):
                if not re.match(r"CREATE\s+OR\s+REPLACE\b", lead):
                    add(line, "create-without-or-replace", code)
                continue
            for obj in IF_NOT_EXISTS_OBJECTS:
                if re.match(rf"CREATE\s+(UNLOGGED\s+|TEMP(ORARY)?\s+)?{obj}\b", lead):
                    if not re.match(rf"CREATE\s+(UNLOGGED\s+|TEMP(ORARY)?\s+)?{obj}\s+IF\s+NOT\s+EXISTS\b", lead):
                        add(line, "create-without-if-not-exists", code)
                    break
            else:
                for obj in DO_GUARDED_OBJECTS:
                    if re.match(rf"CREATE\s+{obj}\b", lead):
                        add(line, "create-without-do-guard", code)
                        break
            continue
        if lead.startswith("ALTER TABLE"):
            added = {m.lower() for m in re.findall(r"\bADD\s+CONSTRAINT\s+([\w\"]+)", code, re.I)}
            dropped = {m.lower() for m in re.findall(r"\bDROP\s+CONSTRAINT\s+IF\s+EXISTS\s+([\w\"]+)", code, re.I)}
            if added - dropped:
                add(line, "add-constraint-without-do-guard", code)
            if re.search(r"\bADD\s+COLUMN\s+(?!IF\s+NOT\s+EXISTS)", code, re.I):
                add(line, "add-column-without-if-not-exists", code)
            if re.search(r"\bDROP\s+CONSTRAINT\s+(?!IF\s+EXISTS)", code, re.I):
                add(line, "drop-constraint-without-if-exists", code)
            continue
        if lead.startswith("INSERT INTO") and not re.search(r"\bON\s+CONFLICT\b", code, re.I):
            add(line, "insert-without-conflict-guard", code)
    return findings


def lint_directory(init_directory: pathlib.Path) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    shell_files: list[str] = []
    for path in sorted(init_directory.iterdir(), key=lambda p: p.name.encode()):
        if path.suffix == ".sh":
            shell_files.append(path.name)
        elif path.suffix == ".sql":
            text = path.read_text(encoding="utf-8")
            findings.extend(lint_sql(path.name, text))
            if declared_class(text) == "update":
                findings.extend(update_rule_findings(path.name, text))
    return findings, shell_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--init-directory", type=pathlib.Path, default=DEFAULT_INIT_DIRECTORY)
    parser.add_argument("--json", action="store_true", help="emit machine-readable findings")
    args = parser.parse_args(argv)
    findings, shell_files = lint_directory(args.init_directory)
    sql_count = len(list(args.init_directory.glob("*.sql")))
    if args.json:
        print(
            json.dumps(
                {
                    "passed": not findings,
                    "sql_files": sql_count,
                    "shell_files_not_applied_in_demo": shell_files,
                    "findings": [asdict(f) for f in findings],
                },
                indent=2,
            )
        )
    else:
        for finding in findings:
            print(f"{finding.file}:{finding.line}: {finding.rule}: {finding.statement}")
        print(
            f"init-chain-lint: {sql_count} sql files, {len(findings)} findings, "
            f"shell files not applied in Demo: {', '.join(shell_files) or 'none'}"
        )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
