#!/usr/bin/env python3

from pathlib import Path
import sys


def normalize_tree(root: Path) -> None:
    if not root.is_dir():
        raise ValueError(f"generated output does not exist: {root}")

    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lines = [line.rstrip() for line in content.splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        normalized = "\n".join(lines) + "\n"
        if normalized != content:
            path.write_text(normalized, encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        raise ValueError("at least one generated output path is required")
    for argument in sys.argv[1:]:
        normalize_tree(Path(argument))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
