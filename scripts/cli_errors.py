"""Shared fail-closed command-line error handling."""

from __future__ import annotations

import argparse
from typing import NoReturn


def fail_cli(parser: argparse.ArgumentParser, message: str, *, cause: BaseException | None = None) -> NoReturn:
    """Terminate through argparse while preserving an optional causal exception."""
    try:
        parser.error(message)
    except SystemExit as error:
        if cause is not None:
            raise error from cause
        raise
    raise AssertionError("argparse parser.error must terminate")
