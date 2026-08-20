"""Prevent noisy unset-variable interpolation in focused Compose commands."""

from __future__ import annotations

import re
from pathlib import Path


def test_compose_variables_have_explicit_local_defaults() -> None:
    compose = (Path(__file__).parents[2] / "docker-compose.yml").read_text(encoding="utf-8")
    assert re.findall(r"\$\{[A-Z0-9_]+\}", compose) == []