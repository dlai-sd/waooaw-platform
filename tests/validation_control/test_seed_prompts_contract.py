"""Executable contracts for the prompt seeding utility."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[2]


def load_seed_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed_prompts", ROOT / "scripts/seed-prompts.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_prompt_block_preserves_governance_metadata(tmp_path: Path) -> None:
    module = load_seed_module()
    source = tmp_path / "prompts.md"
    source.write_text(
        """<!-- PROMPT:7:system:FRONTIER:C-045, C-059 -->
Treat this fixture as confidential prompt content.
<!-- END_PROMPT -->
""",
        encoding="utf-8",
    )

    assert module.parse_prompts_from_md(source) == [
        {
            "skill_id": 7,
            "prompt_role": "system",
            "minimum_model_tier": "FRONTIER",
            "constitutional_basis": "C-045, C-059",
            "prompt_text": "Treat this fixture as confidential prompt content.",
        }
    ]


def test_missing_and_malformed_prompt_sources_produce_no_records(tmp_path: Path) -> None:
    module = load_seed_module()
    malformed = tmp_path / "malformed.md"
    malformed.write_text("<!-- PROMPT:not-an-id:system:LOCAL:C-045 -->\ncontent\n", encoding="utf-8")

    assert module.parse_prompts_from_md(tmp_path / "missing.md") == []
    assert module.parse_prompts_from_md(malformed) == []


def test_dry_run_counts_prompt_without_logging_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_seed_module()
    prompt_text = "SECRET_FIXTURE_PROMPT_TEXT"
    source = tmp_path / "synthetic-prompts.md"
    source.write_text(
        f"<!-- PROMPT:1:system:LOCAL:C-045 -->\n{prompt_text}\n<!-- END_PROMPT -->\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "PROMPT_MANIFEST", [("SYNTHETIC", source.name, "AS-SYNTHETIC")])
    monkeypatch.setattr(module, "SKILL_NAMES", {("SYNTHETIC", 1): "Synthetic Skill"})

    inserted = module.seed_prompts("", tmp_path, True, "")
    output = capsys.readouterr().out

    assert inserted == 1
    assert "SYNTHETIC skill=1 role=system tier=LOCAL" in output
    assert "Seed complete: 1 inserted, 0 already up-to-date, 0 errors." in output
    assert prompt_text not in output
