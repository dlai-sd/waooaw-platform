"""
Tests for compiler_diagnostic_router.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from compiler_diagnostic_router import (
    FAMILY_INTERFACE_CONTRACT,
    FAMILY_NULLABILITY,
    FAMILY_REFERENCE_CONFIG,
    FAMILY_SIGNATURE_DRIFT,
    FAMILY_SYMBOL_RESOLUTION,
    FAMILY_UNKNOWN,
    classify_diagnostic_family,
    parse_diagnostic_facts,
)


def test_parse_file_backed_cs7036_fact():
    err = (
        "/tmp/Foo.cs(52,20): error CS7036: There is no argument given that corresponds "
        "to the required parameter 'logger' of 'Svc.Svc(ILogger<Svc>)'"
    )
    facts = parse_diagnostic_facts(err)
    assert len(facts) == 1
    assert facts[0].code == "CS7036"
    assert facts[0].line == 52
    assert facts[0].file_path.endswith("Foo.cs")


def test_signature_drift_family_for_cs7036():
    facts = parse_diagnostic_facts("error CS7036: missing argument")
    assert classify_diagnostic_family(facts) == FAMILY_SIGNATURE_DRIFT


def test_nullability_family_for_cs0266_and_cs8629():
    facts = parse_diagnostic_facts("error CS0266: x\nwarning CS8629: y")
    assert classify_diagnostic_family(facts) == FAMILY_NULLABILITY


def test_symbol_resolution_family_for_cs0246():
    facts = parse_diagnostic_facts("error CS0246: type not found")
    assert classify_diagnostic_family(facts) == FAMILY_SYMBOL_RESOLUTION


def test_interface_contract_family_for_cs0505():
    facts = parse_diagnostic_facts("error CS0505: override is not a function")
    assert classify_diagnostic_family(facts) == FAMILY_INTERFACE_CONTRACT


def test_reference_config_family_for_nu_msb():
    facts = parse_diagnostic_facts("error NU1101: package not found")
    assert classify_diagnostic_family(facts) == FAMILY_REFERENCE_CONFIG


def test_unknown_family_for_empty_input():
    facts = parse_diagnostic_facts("")
    assert classify_diagnostic_family(facts) == FAMILY_UNKNOWN
