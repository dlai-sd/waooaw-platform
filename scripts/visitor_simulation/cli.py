# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""Command line: ``python -m visitor_simulation run|compare``."""

import argparse
import logging
import os
import sys
from collections.abc import Sequence

from visitor_simulation.client import VisitorApiError, VisitorTransportError
from visitor_simulation.compare import NOISE_BASES, ReportError, compare_reports, load_report, render_markdown, write_comparison
from visitor_simulation.customer import ModelNotConfigured
from visitor_simulation.personas import PersonaError, select_personas
from visitor_simulation.runner import DEFAULT_OUTPUT, INJECTIONS, MODELS, RunConfig, parse_inject, run_suite, write_outputs

EXIT_OK = 0
EXIT_GATE_FAILED = 1
EXIT_USAGE = 2
EXIT_RUN_ABORTED = 3
DEFAULT_SECRET_ENV = "VISITOR_SIMULATOR_SECRET"  # noqa: S105 - the environment variable name, not a secret


class Reporter:
    """Console output for the CLI."""

    def __init__(self, stream: object = None) -> None:
        self._stream = stream or sys.stdout

    def line(self, text: str = "") -> None:
        self._stream.write(text + "\n")  # type: ignore[attr-defined]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visitor_simulation", description="WAOOAW simulated-customer evaluation harness", allow_abbrev=False
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run every persona against a visitor API and write a report", allow_abbrev=False)
    run.add_argument("--base-url", required=True, help="visitor API base URL, for example https://api.demo.waooaw.com")
    run.add_argument(
        "--secret-env",
        default=DEFAULT_SECRET_ENV,
        help=f"name of the environment variable holding the simulator secret (default {DEFAULT_SECRET_ENV})",
    )
    run.add_argument("--runs", type=int, default=20, help="runs per persona (default 20)")
    run.add_argument("--seed", type=int, default=1, help="base seed; use a fresh seed per run against a deployed API")
    run.add_argument("--personas", default="all", help="comma-separated persona ids or 'all'")
    run.add_argument("--inject", action="append", default=[], help=f"failure injection ({', '.join(INJECTIONS)}); repeatable")
    run.add_argument("--output", default=DEFAULT_OUTPUT, help=f"output directory (default {DEFAULT_OUTPUT})")
    run.add_argument("--model", choices=MODELS, default="scripted", help="free-text wording model (default scripted)")
    run.add_argument("--max-turns", type=int, default=30, help="hard turn cap per conversation")
    run.add_argument("--max-model-calls", type=int, default=5000, help="hard model-call cap per run")
    run.add_argument("--timeout", type=float, default=10.0, help="per-request timeout in seconds")
    run.add_argument("--judge-repeats", type=int, default=1, help="score each criterion N times and take the median")
    run.add_argument("--forbidden-claim", action="append", default=[], help="extra forbidden claim; repeatable")

    compare = sub.add_parser("compare", help="gate a new report against a baseline report", allow_abbrev=False)
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--new", required=True)
    compare.add_argument("--min-lift", type=float, default=None, help="required relative lift of full success + lead rate")
    compare.add_argument("--noise-multiplier", type=float, default=1.0)
    compare.add_argument("--noise-floor", type=float, default=0.0)
    compare.add_argument(
        "--noise-basis",
        choices=NOISE_BASES,
        default="std",
        help="std: run-to-run standard deviation (default); stderr: that deviation divided by sqrt(runs)",
    )
    compare.add_argument("--output", default=DEFAULT_OUTPUT)
    return parser


def _run(args: argparse.Namespace, out: Reporter) -> int:
    secret = os.environ.get(args.secret_env, "")
    if not secret:
        out.line("error: the simulator credential variable named by --secret-env is not set")
        return EXIT_USAGE
    if args.runs < 1 or args.max_turns < 1 or args.judge_repeats < 1:
        out.line("error: --runs, --max-turns and --judge-repeats must be at least 1")
        return EXIT_USAGE
    ids = [p.strip() for p in args.personas.split(",") if p.strip()]
    config = RunConfig(
        base_url=args.base_url,
        secret=secret,
        runs=args.runs,
        seed=args.seed,
        personas=select_personas(ids),
        inject=parse_inject(args.inject),
        model=args.model,
        max_turns=args.max_turns,
        max_model_calls=args.max_model_calls,
        timeout=args.timeout,
        judge_repeats=args.judge_repeats,
        forbidden_claims=tuple(args.forbidden_claim),
    )
    result = run_suite(config)
    paths = write_outputs(result, args.output)
    overall = result.report["overall"]
    out.line(
        f"runs: {overall.get('runs', 0)}; failure rate: {overall.get('failureRate', 0):.1%}; "
        f"policy violations: {overall.get('policyViolationTotal', 0)}"
    )
    for path in paths:
        out.line(f"wrote {path}")
    if result.report["capExceeded"]:
        out.line(f"error: run stopped early: {result.report['capExceeded']}")
        return EXIT_RUN_ABORTED
    return EXIT_OK


def _compare(args: argparse.Namespace, out: Reporter) -> int:
    comparison = compare_reports(
        load_report(args.baseline),
        load_report(args.new),
        min_lift=args.min_lift,
        noise_multiplier=args.noise_multiplier,
        noise_floor=args.noise_floor,
        noise_basis=args.noise_basis,
    )
    write_comparison(comparison, args.output)
    out.line(render_markdown(comparison))
    return EXIT_OK if comparison.gate_passed else EXIT_GATE_FAILED


def main(argv: Sequence[str] | None = None, *, reporter: Reporter | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr)
    out = reporter or Reporter()
    args = build_parser().parse_args(argv)
    try:
        return _run(args, out) if args.command == "run" else _compare(args, out)
    except (PersonaError, ReportError, ModelNotConfigured, ValueError) as exc:
        out.line(f"error: {exc}")
        return EXIT_USAGE
    except (VisitorApiError, VisitorTransportError) as exc:
        out.line(f"error: visitor API call failed: {type(exc).__name__} {getattr(exc, 'status', '')}".rstrip())
        return EXIT_RUN_ABORTED
