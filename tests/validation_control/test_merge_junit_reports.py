import xml.etree.ElementTree as ET

from scripts.validation_control.merge_junit_reports import merge


def test_merge_preserves_suites_and_aggregates_counts(tmp_path) -> None:
    customer = tmp_path / "customer.xml"
    service = tmp_path / "service.xml"
    output = tmp_path / "business-platform.xml"
    customer.write_text(
        '<testsuites><testsuite name="customer" tests="2" failures="1" errors="0" skipped="0" time="1.25" /></testsuites>',
        encoding="utf-8",
    )
    service.write_text(
        '<testsuite name="service" tests="3" failures="0" errors="1" skipped="1" time="2.5" />',
        encoding="utf-8",
    )

    merge(output, [customer, service])

    root = ET.parse(output).getroot()
    assert root.attrib == {
        "name": "business-platform-rest-contract",
        "tests": "5",
        "failures": "1",
        "errors": "1",
        "skipped": "1",
        "time": "3.750000",
    }
    assert [suite.get("name") for suite in root.findall("testsuite")] == [
        "customer",
        "service",
    ]