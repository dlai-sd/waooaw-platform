"""Prevent noisy unset-variable interpolation in focused Compose commands."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


COMPOSE_FILE = Path(__file__).parents[2] / "docker-compose.yml"


def test_compose_variables_have_explicit_local_defaults() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    assert re.findall(r"\$\{[A-Z0-9_]+\}", compose) == []


def test_temporal_uses_supported_postgres_driver() -> None:
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    assert compose["services"]["temporal"]["environment"]["DB"] == "postgres12"