# Implements: scripts/autonomous_sprint_runner.py refactored into modular package
# constitutional_basis: C-059 (Evidence First), C-065 (SDLC Separation), C-077 (Cost Ceiling)
# ib_item: IB-009
"""
runner/ — autonomous sprint runner package

Extracted from autonomous_sprint_runner.py for industry-standard modularity.
The top-level autonomous_sprint_runner.py remains the entry-point CLI script
(RUNNER_ANCHOR + TASK_HANDLERS + main()) while this package holds all
extracted functional concerns.

Package layout:
  constants.py     — REPO_ROOT, paths, write-boundary constants
  state.py         — shared mutable runtime state (_MONITOR_SIGNAL, _INFRA_ERROR_TASKS)
  git_ops.py       — shell/git/gh helpers
  system_prompts.py — constitutional system prompt + stack expert blocks
  sprint_ops.py    — sprint state parsing, phase gate, integrity checks
  llm_codegen.py   — LLM call (call_llm, call_llm_via_magiclm), file parse/write/validate
  task_executor.py — execute_with_llm, flag_spec_gap
  legacy_handlers.py — per-WC deterministic handlers (WC011–WC015)
"""
from runner.constants import REPO_ROOT, STATE_FILE, EVIDENCE_LOG, ALLOWED_WRITE_ROOTS  # noqa: F401
from runner.state import _MONITOR_SIGNAL, _INFRA_ERROR_TASKS  # noqa: F401
from runner.git_ops import run, git, gh, set_output, record_evidence  # noqa: F401
from runner.system_prompts import (  # noqa: F401
    _BASE_SYSTEM_PROMPT, _STACK_EXPERTS, _TASK_STACK_MAP,
    _build_system_prompt, CONSTITUTIONAL_SYSTEM_PROMPT, get_branch_context,
)
from runner.sprint_ops import (  # noqa: F401
    parse_sprint_state, check_platform_phase_gate, run_spec_validation,
    update_sprint_state, run_runner_integrity_checks,
)
from runner.llm_codegen import (  # noqa: F401
    call_llm, call_llm_via_magiclm,
    parse_llm_files, write_llm_files, validate_written_files,
)
from runner.task_executor import execute_with_llm, flag_spec_gap  # noqa: F401
from runner.legacy_handlers import (  # noqa: F401
    execute_wc011_01, execute_wc011_02, execute_wc011_03,
    execute_wc011_04, execute_wc011_05, execute_wc011_07,
    execute_wc012_01,
    _generate_wc012_02a_evaluator_interfaces,
    _generate_wc012_02c_prep,
    _generate_wc012_03a_data_layer,
    _generate_wc012_04a_emergency_stop_entities,
    execute_wc013_01, execute_wc014_01, execute_wc015_01,
    _skip_schemathesis_gate,
)
