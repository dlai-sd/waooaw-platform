#!/usr/bin/env python3
"""Prepare and validate a commit-bound pull-request body before PR creation."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import yaml

from precheck_orchestrator import EVIDENCE_FILE_NAME, PrecheckNode, run_prechecks
from validate_author_review import SECTION, validate_author_review
from validate_c059 import read_commits, validate_commit, validate_pr_body
from validate_requirement_ledger import validate_changed_ledgers
from validate_runtime_lifecycle_evidence import runtime_gate_required
from validation_policy import classify_paths, validate_policy
from validation_control.local_catalog_gate import gate_execution_identity

AUTHOR_REVIEW = """## Author Review

<!-- Generated after final push by scripts/prepare_pr_body.py. -->
- [x] Reviewed the complete diff against the authorized scope
- [x] Reviewed test and quality-gate results
- [x] Reviewed security, constitutional, and rollback impact
- [x] Resolved every finding or recorded no findings

**Reviewed Commit:** {head}
**Author Review Result:** PASS

"""
RUNTIME_EVIDENCE_SECTION = re.compile(
    r"^## Pre-PR Runtime Evidence\s*$\n.*?(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
VALIDATION_POLICY_PATH = Path(__file__).resolve().parents[1] / "validation/engineering-validation.yaml"
PRECHECK_GRAPH_VERSION = "wc104-prechecks-v4"
PRECHECK_CONFIGURATION_PATHS = (
    Path(__file__),
    Path(__file__).with_name("precheck_orchestrator.py"),
    Path(__file__).parent / "validation_control/local_catalog_gate.py",
    Path(__file__).parent / "validation_control/catalog_execution.py",
    Path(__file__).parent / "validation_control/orchestrator.py",
    Path(__file__).parent / "validation_control/runner_supply.py",
    Path(__file__).parent / "validation_control/run_gitleaks_gate.sh",
    VALIDATION_POLICY_PATH,
    Path(__file__).resolve().parents[1] / "docker-compose.yml",
    Path(__file__).with_name("run_release_qualification.sh"),
)


def probe_atomic_output(path: Path) -> None:
    """Prove that a final output can be created and atomically replaced."""
    resolved = path.expanduser().resolve()
    parent = resolved.parent
    if not parent.is_dir() or not os.access(parent, os.W_OK):
        raise ValueError(f"output directory is not writable: {parent}")
    if resolved.exists():
        writable_bits = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
        if resolved.stat().st_mode & writable_bits == 0 or not os.access(resolved, os.W_OK):
            raise ValueError(f"output file is not writable: {resolved}")

    temporary = parent / f".{resolved.name}.wc104-probe-{os.getpid()}.tmp"
    replacement = parent / f".{resolved.name}.wc104-probe-{os.getpid()}"
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write("wc104-output-probe\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(replacement)
    except OSError as error:
        raise ValueError(f"output does not support atomic replacement: {resolved}") from error
    finally:
        temporary.unlink(missing_ok=True)
        replacement.unlink(missing_ok=True)


def execution_preflight(
    repository_root: Path,
    body_file: Path,
    expected_worktree: Path,
    expected_head: str,
    local_head: str,
    *,
    require_docker: bool,
) -> None:
    """Reject execution-contract defects before starting any costly gate."""
    failures: list[str] = []
    if not expected_worktree.is_absolute():
        failures.append("--expected-worktree must be an absolute path")
    elif repository_root.resolve() != expected_worktree.resolve():
        failures.append(f"selected worktree is {repository_root.resolve()}, expected {expected_worktree.resolve()}")
    if local_head != expected_head:
        failures.append(f"local HEAD is {local_head}, expected {expected_head}")

    home = Path(os.environ.get("HOME", ""))
    if not home.is_absolute() or not home.is_dir() or not os.access(home, os.W_OK):
        failures.append("HOME must name an existing writable absolute directory")
    for output in (body_file, body_file.with_suffix(".precheck-evidence.json")):
        try:
            probe_atomic_output(output)
        except ValueError as error:
            failures.append(str(error))
    if failures:
        raise ValueError("execution preflight: " + "; ".join(failures))

    try:
        tracked_changes = git("status", "--porcelain", "--untracked-files=no")
        if tracked_changes:
            failures.append("tracked worktree changes must be committed before PR preparation")
    except subprocess.CalledProcessError:
        failures.append("git cannot read the worktree; configure its exact path as a safe.directory")

    if require_docker:
        required_tools = ("bash", "docker", "jq")
        missing = [tool for tool in required_tools if shutil.which(tool) is None]
        if missing:
            failures.append(f"required executables are unavailable: {', '.join(missing)}")
        else:
            docker = shutil.which("docker")
            assert docker is not None
            for label, command in (
                ("Docker daemon", (docker, "info")),
                ("Docker Compose", (docker, "compose", "version")),
                ("Docker Buildx", (docker, "buildx", "version")),
            ):
                completed = subprocess.run(command, check=False, capture_output=True, text=True)  # noqa: S603
                if completed.returncode != 0:
                    failures.append(f"{label} is unavailable")
            socket = Path("/var/run/docker.sock")
            if socket.exists() and not os.access(socket, os.R_OK | os.W_OK):
                failures.append(f"Docker socket is not readable and writable: {socket}")

    if failures:
        raise ValueError("execution preflight: " + "; ".join(failures))


def git(*arguments: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *arguments],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def authoritative_remote_head(remote: str) -> str:
    branch = git("branch", "--show-current")
    if not branch:
        raise ValueError("current checkout must be a named branch")
    remote_record = git("ls-remote", "--heads", remote, f"refs/heads/{branch}")
    if not remote_record:
        raise ValueError(f"branch {branch!r} is not pushed to {remote!r}")
    return remote_record.split(maxsplit=1)[0]


def preparation_head(local_head: str, remote_head: str, allow_unpushed_head: bool) -> str:
    if local_head != remote_head and not allow_unpushed_head:
        raise ValueError(f"local HEAD {local_head} does not match pushed branch HEAD {remote_head}")
    return local_head if allow_unpushed_head else remote_head


def prepare_body(body: str, head: str) -> str:
    match = SECTION.search(body)
    if match is None:
        raise ValueError("PR body must contain the `## Author Review` template section")
    return body[: match.start()] + AUTHOR_REVIEW.format(head=head) + body[match.end() :]


def add_runtime_evidence(body: str, evidence: dict[str, object]) -> str:
    if evidence.get("passed") is not True:
        raise ValueError("runtime lifecycle evidence must report passed=true")
    rendered = (
        "## Pre-PR Runtime Evidence\n\n"
        "Generated by `scripts/run_goal006_runtime_lifecycle_gate.sh` before PR creation.\n\n"
        "```json\n"
        f"{json.dumps(evidence, indent=2, sort_keys=True)}\n"
        "```\n\n"
    )
    match = RUNTIME_EVIDENCE_SECTION.search(body)
    if match is not None:
        return body[: match.start()] + rendered + body[match.end() :]
    author_review = SECTION.search(body)
    if author_review is None:
        raise ValueError("PR body must contain the `## Author Review` template section")
    return body[: author_review.start()] + rendered + body[author_review.start() :]


def run_runtime_gate(body_file: Path, head: str) -> dict[str, object]:
    repository_root = Path(git("rev-parse", "--show-toplevel"))
    evidence_file = body_file.with_suffix(".runtime-evidence.json")
    subprocess.run(  # noqa: S603
        [str(repository_root / "scripts/run_goal006_runtime_lifecycle_gate.sh"), str(evidence_file)],
        cwd=repository_root,
        check=True,
    )
    evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
    return validate_runtime_evidence_head(evidence, head)


def load_runtime_evidence(evidence_file: Path, head: str) -> dict[str, object]:
    evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
    return validate_runtime_evidence_head(evidence, head)


def validate_runtime_evidence_head(evidence: dict[str, object], head: str) -> dict[str, object]:
    evidence_head = str(evidence.get("commit_sha", ""))
    if evidence_head != head:
        git_executable = shutil.which("git")
        if git_executable is None:
            raise ValueError("git executable is required to validate runtime evidence ancestry")
        ancestor = subprocess.run(  # noqa: S603
            [git_executable, "merge-base", "--is-ancestor", evidence_head, head],
            check=False,
            capture_output=True,
            text=True,
        )
        if ancestor.returncode != 0:
            raise ValueError("runtime lifecycle evidence is not an ancestor of the selected branch HEAD")
        intervening_files = git("diff", "--name-only", f"{evidence_head}..{head}").splitlines()
        if runtime_gate_required(intervening_files):
            raise ValueError("runtime lifecycle evidence predates runtime-affecting changes")
    return evidence


def selected_prechecks(changed_files: list[str]) -> set[str]:
    loaded = yaml.safe_load(VALIDATION_POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("validation policy root must be a mapping")
    selection = classify_paths(loaded, changed_files)
    selected = selection.get("selected_prechecks")
    if not isinstance(selected, list) or not all(isinstance(gate, str) for gate in selected):
        raise ValueError("validation policy returned invalid prechecks")
    return set(selected)


def validate_static_repository(repository_root: Path) -> list[str]:
    violations: list[str] = []
    try:
        loaded = yaml.safe_load(VALIDATION_POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        violations.append(f"validation catalog cannot be loaded: {error}")
    else:
        if not isinstance(loaded, dict):
            violations.append("validation catalog root must be a mapping")
        else:
            violations.extend(f"validation catalog: {violation}" for violation in validate_policy(loaded))

    compose = subprocess.run(
        ["docker", "compose", "config", "--quiet"],  # noqa: S607
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if compose.returncode != 0:
        detail = compose.stderr.strip() or compose.stdout.strip() or "configuration is invalid"
        violations.append(f"Docker Compose: {detail}")
    return violations


def business_platform_gate_required(changed_files: list[str]) -> bool:
    return "business_platform" in selected_prechecks(changed_files)


def release_qualification_gate_required(changed_files: list[str]) -> bool:
    return "release_qualification" in selected_prechecks(changed_files)


def expected_pr_labels(branch: str) -> tuple[str, str, str]:
    if branch.startswith("fix/"):
        tier = "tier:1-bugfix"
    elif branch.startswith("agent/"):
        tier = "tier:3-constitutional"
    else:
        tier = "tier:2-feature"
    return tier, "status:pr-open", "awaiting:review"


def changed_files_digest(changed_files: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(changed_files)).encode()).hexdigest()


def configuration_digest() -> str:
    digest = hashlib.sha256()
    for path in PRECHECK_CONFIGURATION_PATHS:
        digest.update(str(path.relative_to(Path(__file__).resolve().parents[1])).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def runner_digest(nodes: list[PrecheckNode]) -> str:
    graph = [
        {
            "name": node.name,
            "command": node.command,
            "heavy": node.heavy,
            "dependencies": node.dependencies,
            "transient_retries": node.transient_retries,
            "catalog_version": node.catalog_version,
            "gate_id": node.gate_id,
            "command_id": node.command_id,
            "gate_implementation_digest": node.gate_implementation_digest,
            "runner_digest": node.runner_digest,
            "environment_digest": node.environment_digest,
            "input_digest": node.input_digest,
            "input_patterns": node.input_patterns,
        }
        for node in nodes
    ]
    return hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()


def gate_input_digest(head: str, patterns: tuple[str, ...]) -> str:
    entries: list[tuple[str, str]] = []
    for line in git("ls-tree", "-r", "--full-tree", head).splitlines():
        metadata, separator, path = line.partition("\t")
        fields = metadata.split()
        if separator and len(fields) == 3 and any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns):
            entries.append((path, metadata))
    payload = {"patterns": patterns, "entries": sorted(entries)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_precheck_evidence(
    evidence: dict[str, object],
    base_sha: str,
    head: str,
    changed_file_digest: str,
    expected_configuration_digest: str,
    expected_runner_digest: str,
    graph_version: str = PRECHECK_GRAPH_VERSION,
) -> dict[str, object]:
    if evidence.get("passed") is not True:
        raise ValueError("precheck evidence must report passed=true")
    if evidence.get("base_sha") != base_sha or evidence.get("commit_sha") != head:
        raise ValueError("precheck evidence is not bound to the selected base and branch HEAD")
    if evidence.get("schema") != "waooaw.pr-prechecks/v4":
        raise ValueError("precheck evidence schema is not trusted")
    if evidence.get("changed_file_digest") != changed_file_digest:
        raise ValueError("precheck evidence is not bound to the selected changed files")
    if evidence.get("graph_version") != graph_version:
        raise ValueError("precheck evidence is not bound to the current gate graph")
    if evidence.get("configuration_digest") != expected_configuration_digest:
        raise ValueError("precheck evidence is not bound to the current gate configuration")
    if evidence.get("runner_digest") != expected_runner_digest:
        raise ValueError("precheck evidence is not bound to the current runner graph")
    return evidence


def precheck_nodes(
    repository_root: Path,
    git_common_dir: Path,
    base: str,
    head: str,
    changed_files: list[str],
) -> list[PrecheckNode]:
    applicable_prechecks = selected_prechecks(changed_files)
    loaded = yaml.safe_load(VALIDATION_POLICY_PATH.read_text(encoding="utf-8"))
    precheck_config = loaded.get("prechecks") if isinstance(loaded, dict) else None
    if not isinstance(precheck_config, dict):
        raise ValueError("validation catalog prechecks must be a mapping")
    python = shutil.which("python3")
    if python is None:
        raise ValueError("python3 executable is required for PR prechecks")
    local_executor = repository_root / "scripts/validation_control/local_catalog_gate.py"
    nodes: list[PrecheckNode] = []
    for name in ("gitleaks", "business_platform", "release_qualification"):
        if name not in applicable_prechecks:
            continue
        config = precheck_config.get(name)
        gate_id = config.get("gate") if isinstance(config, dict) else None
        if not isinstance(gate_id, str) or not gate_id:
            raise ValueError(f"validation catalog precheck {name} has no gate")
        input_patterns_value = config.get("inputs")
        if not isinstance(input_patterns_value, list) or not all(
            isinstance(pattern, str) and pattern for pattern in input_patterns_value
        ):
            raise ValueError(f"validation catalog precheck {name} has no declared inputs")
        input_patterns = tuple(input_patterns_value)
        identity = gate_execution_identity(repository_root, gate_id, head)
        nodes.append(
            PrecheckNode(
                name=name,
                command=(
                    python,
                    str(local_executor),
                    "--gate",
                    gate_id,
                    "--base",
                    base,
                    "--head",
                    head,
                    "--git-common-dir",
                    str(git_common_dir),
                ),
                heavy=name != "gitleaks",
                input_digest=gate_input_digest(head, input_patterns),
                input_patterns=input_patterns,
                **identity,
            )
        )
    return nodes


def run_ci_prechecks(base: str, head: str, changed_files: list[str]) -> dict[str, object]:
    repository_root = Path(git("rev-parse", "--show-toplevel"))
    git_common_dir = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir"))
    nodes = precheck_nodes(repository_root, git_common_dir, base, head, changed_files)
    artifact_dir = repository_root / "test-results/wc100/prechecks" / head
    prior_evidence = sorted(path for path in artifact_dir.parent.glob(f"*/{EVIDENCE_FILE_NAME}") if path.parent != artifact_dir)
    return run_prechecks(
        nodes,
        base_sha=git("rev-parse", base),
        head_sha=head,
        changed_file_digest=changed_files_digest(changed_files),
        graph_version=PRECHECK_GRAPH_VERSION,
        configuration_digest=configuration_digest(),
        runner_digest=runner_digest(nodes),
        artifact_dir=artifact_dir,
        reuse_evidence_paths=prior_evidence,
    )


def update_pull_request(pr_number: int, body_file: Path, branch: str) -> None:
    command = ["gh", "pr", "edit", str(pr_number), "--body-file", str(body_file)]
    for label in expected_pr_labels(branch):
        command.extend(("--add-label", label))
    subprocess.run(command, check=True)  # noqa: S603


def validate_prepared_body(body: str, base: str, head: str) -> list[str]:
    violations = validate_pr_body(body)
    for subject, commit_body in read_commits(base, head):
        violations.extend(validate_commit(subject, commit_body))
    violations.extend(validate_author_review(body, head))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--expected-worktree", required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="validate the execution environment without reading remote state or running gates",
    )
    parser.add_argument(
        "--allow-unpushed-head",
        action="store_true",
        help="bind an existing PR body before push; rerun without this flag immediately after push",
    )
    parser.add_argument(
        "--runtime-evidence-file",
        type=Path,
        help="reuse lifecycle evidence already generated for the selected commit",
    )
    parser.add_argument(
        "--precheck-evidence-file",
        type=Path,
        help="reuse successful prechecks bound to the selected base and branch HEAD",
    )
    parser.add_argument(
        "--update-pr",
        type=int,
        metavar="NUMBER",
        help="update an existing PR body and labels before pushing the prepared local commit",
    )
    arguments = parser.parse_args()

    try:
        if arguments.update_pr is not None and not arguments.allow_unpushed_head:
            raise ValueError("--update-pr requires --allow-unpushed-head")
        repository_root = Path(git("rev-parse", "--show-toplevel"))
        local_head = git("rev-parse", "HEAD")
        execution_preflight(
            repository_root,
            arguments.body_file,
            arguments.expected_worktree,
            arguments.expected_head,
            local_head,
            require_docker=arguments.preflight_only or arguments.precheck_evidence_file is None,
        )
        if arguments.preflight_only:
            print(f"PR execution preflight passed for {repository_root} at {local_head}")
            return 0
        remote_head = authoritative_remote_head(arguments.remote)
        head = preparation_head(local_head, remote_head, arguments.allow_unpushed_head)
        body = arguments.body_file.read_text(encoding="utf-8")
        changed_files = git("diff", "--name-only", f"{arguments.base}..{head}").splitlines()
        changed_file_digest = changed_files_digest(changed_files)
        base_sha = git("rev-parse", arguments.base)
        ledger_violations = validate_changed_ledgers(repository_root, changed_files)
        if ledger_violations:
            raise ValueError("requirement ledger: " + "; ".join(ledger_violations))
        body = prepare_body(body, head)
        violations = validate_prepared_body(body, arguments.base, head)
        if violations:
            raise ValueError("static PR validation: " + "; ".join(violations))
        repository_violations = validate_static_repository(repository_root)
        if repository_violations:
            raise ValueError("static repository validation: " + "; ".join(repository_violations))
        if arguments.precheck_evidence_file:
            nodes = precheck_nodes(
                repository_root,
                Path(git("rev-parse", "--path-format=absolute", "--git-common-dir")),
                arguments.base,
                head,
                changed_files,
            )
            evidence = json.loads(arguments.precheck_evidence_file.read_text(encoding="utf-8"))
            validate_precheck_evidence(
                evidence,
                base_sha,
                head,
                changed_file_digest,
                configuration_digest(),
                runner_digest(nodes),
            )
        else:
            evidence = run_ci_prechecks(arguments.base, head, changed_files)
            arguments.body_file.with_suffix(".precheck-evidence.json").write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            if evidence.get("passed") is not True:
                raise ValueError(
                    "prechecks failed; first causal gate: "
                    f"{evidence.get('first_causal_failure')}; "
                    f"artifacts: test-results/wc100/prechecks/{head}"
                )
        if runtime_gate_required(changed_files):
            evidence = (
                load_runtime_evidence(arguments.runtime_evidence_file, head)
                if arguments.runtime_evidence_file
                else run_runtime_gate(arguments.body_file, head)
            )
            body = add_runtime_evidence(body, evidence)
        violations = validate_prepared_body(body, arguments.base, head)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"PR body preparation failed: {error}", file=sys.stderr)
        return 1

    if violations:
        print("PR body preparation failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    arguments.body_file.write_text(body, encoding="utf-8")
    if arguments.update_pr is not None:
        update_pull_request(arguments.update_pr, arguments.body_file, git("branch", "--show-current"))
    source = "local pre-push" if arguments.allow_unpushed_head else "pushed"
    print(f"PR body prepared for {source} commit {head}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
