from __future__ import annotations

from pathlib import Path

import pytest

from wc124_init_chain_lint import lint_directory, lint_sql

ROOT = Path(__file__).resolve().parents[2]
INIT_DIRECTORY = ROOT / "infrastructure/postgres/init"


def test_repository_init_chain_meets_the_idempotent_authoring_standard() -> None:
    findings, shell_files = lint_directory(INIT_DIRECTORY)

    assert findings == []
    assert shell_files == ["02-users-and-permissions.sh", "42-demo-marketplace-admission.sh"]


@pytest.mark.parametrize(
    ("sql", "rule"),
    [
        ("CREATE TABLE a.t (id int);", "create-without-if-not-exists"),
        ("CREATE INDEX t_idx ON a.t (id);", "create-without-if-not-exists"),
        ("CREATE SCHEMA a;", "create-without-if-not-exists"),
        ("CREATE FUNCTION a.f() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$;", "create-without-or-replace"),
        ("CREATE TRIGGER trg BEFORE INSERT ON a.t EXECUTE FUNCTION a.f();", "create-without-or-replace"),
        ("CREATE TYPE a.kind AS ENUM ('x');", "create-without-do-guard"),
        ("CREATE ROLE reporter NOLOGIN;", "create-without-do-guard"),
        ("CREATE POLICY p ON a.t USING (true);", "policy-without-drop"),
        (
            "CREATE CONSTRAINT TRIGGER ct AFTER INSERT ON a.t DEFERRABLE FOR EACH ROW EXECUTE FUNCTION a.f();",
            "constraint-trigger-without-drop",
        ),
        ("ALTER TABLE a.t ADD CONSTRAINT ck CHECK (id > 0);", "add-constraint-without-do-guard"),
        ("ALTER TABLE a.t ADD COLUMN name text;", "add-column-without-if-not-exists"),
        ("ALTER TABLE a.t DROP CONSTRAINT ck;", "drop-constraint-without-if-exists"),
        ("INSERT INTO a.t (id) VALUES (1);", "insert-without-conflict-guard"),
        (
            "DO $x$ BEGIN EXECUTE format('CREATE POLICY %I ON a.%I USING (true)', 'p', 't'); END $x$;",
            "dynamic-policy-without-drop",
        ),
    ],
)
def test_lint_rejects_each_non_idempotent_shape(sql: str, rule: str) -> None:
    findings = lint_sql("x.sql", sql)

    assert [finding.rule for finding in findings] == [rule]


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE IF NOT EXISTS a.t (id int);",
        "CREATE OR REPLACE FUNCTION a.f() RETURNS int LANGUAGE sql AS $$ SELECT 1; $$;",
        "DO $g$ BEGIN IF to_regtype('a.kind') IS NULL THEN CREATE TYPE a.kind AS ENUM ('x'); END IF; END $g$;",
        "DROP POLICY IF EXISTS p ON a.t; CREATE POLICY p ON a.t USING (true);",
        "DROP TRIGGER IF EXISTS ct ON a.t; CREATE CONSTRAINT TRIGGER ct AFTER INSERT ON a.t FOR EACH ROW EXECUTE FUNCTION a.f();",
        "ALTER TABLE a.t DROP CONSTRAINT IF EXISTS ck, ADD CONSTRAINT ck CHECK (id > 0);",
        "ALTER TABLE a.t ADD COLUMN IF NOT EXISTS name text;",
        "INSERT INTO a.t (id) VALUES (1) ON CONFLICT DO NOTHING;",
        "DO $s$ BEGIN IF NOT EXISTS (SELECT 1 FROM a.t WHERE id = 1) THEN INSERT INTO a.t (id) VALUES (1); END IF; END $s$;",
        "DO $x$ BEGIN EXECUTE format('DROP POLICY IF EXISTS %I ON a.%I', 'p', 't'); EXECUTE format('CREATE POLICY %I ON a.%I USING (true)', 'p', 't'); END $x$;",
        "DO $x$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tg') THEN EXECUTE format('CREATE TRIGGER tg BEFORE INSERT ON a.t EXECUTE FUNCTION a.f()'); END IF; END $x$;",
        "-- CREATE TABLE a.commented (id int);\nSELECT 'CREATE TABLE a.in_string (id int);';",
    ],
)
def test_lint_accepts_each_idempotent_shape(sql: str) -> None:
    assert lint_sql("x.sql", sql) == []
