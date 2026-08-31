"""Constitutional fail-closed checks for Agent Runtime Adapter v1."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §13
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_cct_paas_01_gateway_contains_no_professional_type_dispatch() -> None:
    source = (ROOT / "src/professional-runtime/adapter_gateway.py").read_text()
    forbidden = ("if professional_type", "match professional_type", "DIGITAL_MARKETING", "TRADING_FO")
    assert not any(token in source for token in forbidden)


def test_cct_ho_02_stop_cannot_be_disabled_by_configuration() -> None:
    source = (ROOT / "src/agent-adapters/runtime_contract/adapter.py").read_text()
    assert "emergency_stop" in source
    assert "ENABLE_STOP" not in source
    assert "DISABLE_STOP" not in source


def test_cct_ef_01_adapter_never_claims_constitutional_success() -> None:
    source_root = ROOT / "src/agent-adapters"
    source = "\n".join(path.read_text() for path in source_root.rglob("*.py"))
    assert "constitutional_success" not in source.lower()
    assert "evidence_accepted" not in source.lower()