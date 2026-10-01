#!/usr/bin/env python3
import argparse
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


def suites(document: ET.Element) -> list[ET.Element]:
    if document.tag == "testsuite":
        return [document]
    if document.tag != "testsuites":
        raise ValueError(f"unsupported JUnit root element: {document.tag}")
    return list(document.findall("testsuite"))


def merge(output: Path, inputs: list[Path]) -> None:
    merged = ET.Element("testsuites", name="business-platform-rest-contract")
    totals: dict[str, float] = {
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "time": 0.0,
    }
    for source in inputs:
        for suite in suites(ET.parse(source).getroot()):  # noqa: S314 - Inputs are local test reports.
            merged.append(suite)
            for field in ("tests", "failures", "errors", "skipped"):
                totals[field] += int(suite.get(field, "0"))
            totals["time"] += float(suite.get("time", "0"))
    if not list(merged) or totals["tests"] == 0:
        raise ValueError("refusing to publish an empty JUnit report")
    for field in ("tests", "failures", "errors", "skipped"):
        merged.set(field, str(int(totals[field])))
    merged.set("time", f"{totals['time']:.6f}")

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(dir=output.parent, prefix=f".{output.name}.")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            ET.ElementTree(merged).write(stream, encoding="utf-8", xml_declaration=True)
        os.replace(temporary_name, output)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("inputs", type=Path, nargs="+")
    args = parser.parse_args()
    merge(args.output, args.inputs)


if __name__ == "__main__":
    main()
