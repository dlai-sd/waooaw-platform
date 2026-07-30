# Implements: tests/runner/test_legacy_handlers.py
# constitutional_basis: C-076 (≥90% coverage), C-059 (Traceability)
"""Tests for runner/legacy_handlers.py — execute_wc011_*, execute_wc012_01,
_generate_wc012_02a_evaluator_interfaces, _generate_wc012_03a_data_layer, etc."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_scripts = str(Path(__file__).parent.parent.parent / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

import runner.legacy_handlers as lh


def _make_mock_git():
    """Return a mock git helper that always returns returncode=0."""
    m = MagicMock()
    m.returncode = 0
    m.stdout = ""
    return lambda args, check=True: m


class TestExecuteWc011_01:
    def test_fails_when_docker_compose_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        (tmp_path / "logs").mkdir()

        def fake_run(cmd, check=True, capture=False):
            m = MagicMock()
            m.returncode = 1
            m.stdout = ""
            m.stderr = "compose error"
            return m

        monkeypatch.setattr(lh, "run", fake_run)
        monkeypatch.setattr(lh, "git", _make_mock_git())
        result = lh.execute_wc011_01()
        assert result is False

    def test_fails_when_service_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        (tmp_path / "logs").mkdir()

        def fake_run(cmd, check=True, capture=False):
            m = MagicMock()
            m.returncode = 0
            # Missing 'temporal' and 'keycloak'
            m.stdout = "constitutional-engine business-platform professional-runtime ai-runtime web postgres"
            m.stderr = ""
            return m

        monkeypatch.setattr(lh, "run", fake_run)
        monkeypatch.setattr(lh, "git", _make_mock_git())
        result = lh.execute_wc011_01()
        assert result is False

    def test_passes_with_all_services(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        (tmp_path / "logs").mkdir()

        all_services = ("constitutional-engine business-platform professional-runtime "
                        "ai-runtime web postgres keycloak temporal")

        def fake_run(cmd, check=True, capture=False):
            m = MagicMock()
            m.returncode = 0
            m.stdout = all_services
            m.stderr = ""
            return m

        mock_git = MagicMock(return_value=MagicMock(returncode=1))
        monkeypatch.setattr(lh, "run", fake_run)
        monkeypatch.setattr(lh, "git", mock_git)
        result = lh.execute_wc011_01()
        assert result is True


class TestExecuteWc011_03:
    def test_fails_when_no_realm_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        (tmp_path / "infrastructure" / "keycloak").mkdir(parents=True)
        result = lh.execute_wc011_03()
        assert result is False

    def test_fails_on_invalid_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        kc_dir = tmp_path / "infrastructure" / "keycloak"
        kc_dir.mkdir(parents=True)
        (kc_dir / "realm.json").write_text("{invalid json}")
        result = lh.execute_wc011_03()
        assert result is False

    def test_passes_on_valid_realm(self, tmp_path, monkeypatch):
        import json
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        kc_dir = tmp_path / "infrastructure" / "keycloak"
        kc_dir.mkdir(parents=True)
        realm = {"realm": "waooaw", "identityProviders": [{"providerId": "google"}]}
        (kc_dir / "realm.json").write_text(json.dumps(realm))
        result = lh.execute_wc011_03()
        assert result is True

    def test_warns_on_wrong_realm_name(self, tmp_path, monkeypatch, capsys):
        import json
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        kc_dir = tmp_path / "infrastructure" / "keycloak"
        kc_dir.mkdir(parents=True)
        realm = {"realm": "wrongname", "identityProviders": []}
        (kc_dir / "realm.json").write_text(json.dumps(realm))
        lh.execute_wc011_03()
        out = capsys.readouterr().out
        assert "WARN" in out or "wrongname" in out


class TestExecuteWc011_04:
    def test_creates_service_directories(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        mock_git = MagicMock(return_value=MagicMock(returncode=1))
        monkeypatch.setattr(lh, "git", mock_git)
        result = lh.execute_wc011_04()
        assert result is True
        for svc in ["constitutional-engine", "business-platform", "professional-runtime", "ai-runtime"]:
            assert (tmp_path / "src" / svc).is_dir()

    def test_writes_readme_with_c059_header(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(lh, "git", MagicMock(return_value=MagicMock(returncode=1)))
        lh.execute_wc011_04()
        readme = tmp_path / "src" / "constitutional-engine" / "README.md"
        assert "C-059" in readme.read_text()

    def test_does_not_overwrite_existing_readme(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(lh, "git", MagicMock(return_value=MagicMock(returncode=1)))
        svc_dir = tmp_path / "src" / "constitutional-engine"
        svc_dir.mkdir(parents=True)
        readme = svc_dir / "README.md"
        readme.write_text("# Original content")
        lh.execute_wc011_04()
        # Original content preserved
        assert readme.read_text() == "# Original content"


class TestExecuteWc011_05:
    def test_fails_when_scripts_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        (tmp_path / "scripts").mkdir()
        result = lh.execute_wc011_05()
        assert result is False

    def test_passes_when_scripts_present_with_shebang(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "setup.sh").write_text("#!/bin/bash\necho hello\n")
        (scripts_dir / "get-dev-token.sh").write_text("#!/bin/bash\necho token\n")
        result = lh.execute_wc011_05()
        assert result is True


class TestExecuteWc011_07:
    def test_creates_secrets_doc(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        (tmp_path / "infrastructure").mkdir()
        monkeypatch.setattr(lh, "git", MagicMock(return_value=MagicMock(returncode=1)))
        result = lh.execute_wc011_07()
        assert result is True
        assert (tmp_path / "infrastructure" / "GITHUB-SECRETS.md").exists()

    def test_skips_if_already_documented(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        infra = tmp_path / "infrastructure"
        infra.mkdir()
        existing = infra / "GITHUB-SECRETS.md"
        existing.write_text("OIDC + Azure Key Vault\nANTHROPIC-API-KEY\n")
        result = lh.execute_wc011_07()
        assert result is True
        # Content should remain unchanged
        assert existing.read_text().startswith("OIDC + Azure Key Vault")


class TestGenerateWc012DataLayer:
    def test_creates_evidence_record(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(lh, "git", MagicMock(return_value=MagicMock(returncode=0)))
        result = lh._generate_wc012_03a_data_layer()
        assert result is True
        evidence_cs = tmp_path / "src" / "constitutional-engine" / "Data" / "Entities" / "EvidenceRecord.cs"
        assert evidence_cs.exists()
        assert "C-027" in evidence_cs.read_text()

    def test_creates_db_context(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(lh, "git", MagicMock(return_value=MagicMock(returncode=0)))
        lh._generate_wc012_03a_data_layer()
        db_cs = tmp_path / "src" / "constitutional-engine" / "Data" / "ConstitutionalDbContext.cs"
        assert db_cs.exists()
        assert "ConstitutionalDbContext" in db_cs.read_text()


class TestGenerateWc012_04aEmergencyStop:
    def test_creates_emergency_stop_event(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(lh, "git", MagicMock(return_value=MagicMock(returncode=0)))
        result = lh._generate_wc012_04a_emergency_stop_entities()
        assert result is True
        es_cs = tmp_path / "src" / "constitutional-engine" / "EmergencyStop" / "EmergencyStopEvent.cs"
        assert es_cs.exists()
        assert "C-001" in es_cs.read_text()


class TestGenerateWc012_02cPrep:
    def test_creates_fake_server_call_context(self, tmp_path, monkeypatch):
        monkeypatch.setattr(lh, "REPO_ROOT", tmp_path)
        result = lh._generate_wc012_02c_prep()
        assert result is True
        fake_ctx = (tmp_path / "tests" / "constitutional-engine.Tests" / "Evaluators"
                    / "FakeServerCallContext.cs")
        assert fake_ctx.exists()
        content = fake_ctx.read_text()
        # All overrides must be properties, not methods (CS0505 prevention)
        assert "protected override string MethodCore" in content
        assert "protected override CancellationToken CancellationTokenCore" in content
