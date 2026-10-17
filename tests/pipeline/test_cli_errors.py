import argparse

import pytest

from scripts.cli_errors import fail_cli


def test_fail_cli_preserves_argparse_error_contract(capsys: pytest.CaptureFixture[str]) -> None:
    parser = argparse.ArgumentParser(prog="qualified-command")
    cause = ValueError("invalid input")

    with pytest.raises(SystemExit) as raised:
        fail_cli(parser, str(cause), cause=cause)

    assert raised.value.code == 2
    assert raised.value.__cause__ is cause
    assert "qualified-command: error: invalid input" in capsys.readouterr().err


def test_fail_cli_rejects_a_parser_that_returns() -> None:
    class ReturningParser(argparse.ArgumentParser):
        def error(self, message: str) -> None:
            assert message == "invalid input"

    with pytest.raises(AssertionError, match="must terminate"):
        fail_cli(ReturningParser(), "invalid input")
