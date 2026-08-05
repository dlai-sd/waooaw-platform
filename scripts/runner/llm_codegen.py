# Implements: scripts/runner/llm_codegen.py
# constitutional_basis: ADR-030 (code generation protocol), C-059, C-077 (cost ceiling)
# ib_item: IB-020
"""
LLM code generation: call_llm_via_magiclm() (governed bridge), _call_llm_direct() (private fallback),
parse_llm_files(), write_llm_files(), validate_written_files().

Prompt caching (ADR-030 §4 — "procure token once"):
  call_llm_via_magiclm() marks the system prompt cache_control: ephemeral so retry
  attempts reuse the cached token block from Anthropic — up to 90% cost reduction.
  _call_llm_direct() is the private fallback used when MagicLLM is unavailable.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from runner.constants import REPO_ROOT, ALLOWED_WRITE_ROOTS
from runner.git_ops import record_evidence
from runner.state import _MONITOR_SIGNAL
from runner.system_prompts import _build_system_prompt, _TASK_STACK_MAP


def _call_llm_direct(
    task_id: str,
    task_description: str,
    spec_content: str,
    constitutional_check: str,
    model_hint: str = "reasoning",
    max_tokens: int = 10000,
    attempt: int = 1,
) -> str | None:
    """
    Direct Anthropic call — private fallback used by call_llm_via_magiclm.
    Returns raw LLM response string, or None on failure.

    For model_hint='reasoning' tasks: enables extended thinking (budget_tokens=8000).
    Prompt caching enabled — system prompt marked cache_control: ephemeral.

    constitutional_basis: ADR-030 (code generation protocol), C-077 (cost ceiling)
    ib_item: IB-020
    """
    if model_hint not in ("reasoning", "auto"):
        return None  # model_hint: none — no LLM needed

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(f"  WARN: ANTHROPIC_API_KEY not set — cannot call LLM for {task_id}")
        return None

    # Thinking mode: 'enabled' with controlled budget.
    THINKING_OVERHEAD = 8000
    THINKING_BUDGET   = 8000
    use_thinking = model_hint == "reasoning"
    effective_max_tokens = (max_tokens + THINKING_OVERHEAD) if use_thinking else max_tokens

    try:
        import urllib.request
        import json as json_mod

        calibration_prefix = (
            "## SELF-CALIBRATION (complete before writing any <file> block)\n"
            "From the spec and BRANCH CONTEXT below, derive your implementation plan:\n"
            "1. Which files already exist on the branch? (check BRANCH CONTEXT — do NOT regenerate them)\n"
            "2. Which NEW files will you create? List each with its exact namespace declaration.\n"
            "3. For each file: what using directives does it need? Cross-check the namespace reference above.\n"
            "4. Does ConstitutionalDbContext exist yet? (only if WC012-03a is in BRANCH CONTEXT)\n"
            "5. Confirm your plan matches the namespace reference in the system prompt before proceeding.\n\n"
            "Then write ONLY the new/extended files using <file path=\"...\"> blocks.\n\n"
        )

        user_prompt = (
            f"{calibration_prefix}"
            f"Task: {task_id} — {task_description}\n\n"
            f"Spec context:\n{spec_content}\n\n"
            f"Constitutional check (must pass):\n{constitutional_check}\n\n"
            f"Generate the implementation files now. "
            f"Use <file path=\"...\"> blocks for each file. "
            f"Include unit tests in tests/ directory."
        )

        model_id = os.environ.get("SPRINT_LLM_MODEL", "claude-sonnet-4-6")
        system_text = _build_system_prompt(task_id)

        payload: dict = {
            "model": model_id,
            "max_tokens": effective_max_tokens,
            # Prompt caching (ADR-030 §4): mark system prompt as cacheable so
            # retry attempts reuse the cached token block (C-077 cost reduction).
            "system": [{"type": "text", "text": system_text,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": user_prompt}],
        }

        if use_thinking:
            payload["thinking"] = {"type": "enabled", "budget_tokens": THINKING_BUDGET}
            payload["temperature"] = 1
            print(f"  Thinking: enabled | budget={THINKING_BUDGET} | effective_max={effective_max_tokens} "
                  f"(code={max_tokens} + overhead={THINKING_OVERHEAD})")
        else:
            payload["temperature"] = 0

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json_mod.dumps(payload).encode(),
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "prompt-caching-2024-07-31",
                "content-type": "application/json",
            },
        )
        prompt_chars = len(json_mod.dumps(payload))
        print(f"  REQ:  {task_id} attempt={attempt} | prompt={prompt_chars:,} chars | max_tokens={effective_max_tokens} (code={max_tokens})")
        timeout_floor = int(os.environ.get("LLM_API_TIMEOUT_FLOOR_S", "180"))
        timeout_ceiling = int(os.environ.get("LLM_API_TIMEOUT_CEILING_S", "420"))
        scaled_timeout = (effective_max_tokens // 50) * 3
        api_timeout = max(timeout_floor, min(timeout_ceiling, scaled_timeout))
        t_start = __import__('time').monotonic()
        with urllib.request.urlopen(req, timeout=api_timeout) as resp:
            result = json_mod.loads(resp.read())
        latency_s = __import__('time').monotonic() - t_start
        content = result.get("content", [])
        text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
        usage = result.get("usage", {})
        tokens_in  = usage.get("input_tokens", 0)
        tokens_out = usage.get("output_tokens", 0)
        cache_read  = usage.get("cache_read_input_tokens", 0)
        cache_write = usage.get("cache_creation_input_tokens", 0)
        thinking_blocks = sum(1 for b in content if b.get("type") == "thinking")
        thinking_chars  = sum(len(b.get("thinking", "")) for b in content if b.get("type") == "thinking")
        stop_reason = result.get("stop_reason", "unknown")
        text_chars  = len(text)
        block_types = [b.get("type") for b in content]
        text_snippet = text[:400].replace("\n", " ") if text else "(empty)"
        print(f"  LLM:  {task_id} attempt={attempt} → {tokens_in} in / {tokens_out} out | "
              f"latency={latency_s:.1f}s | stop={stop_reason!r}")
        if cache_read or cache_write:
            print(f"  CACHE: read={cache_read} write={cache_write} (prompt-caching active)")
        if thinking_blocks:
            print(f"  THINK: {thinking_blocks} block(s), {thinking_chars:,} chars")
        print(f"  RESP: block_types={block_types} | text_chars={text_chars:,}")
        print(f"  TEXT: {text_snippet}")
        record_evidence(
            "llm_call",
            task=task_id, attempt=attempt,
            tokens_in=tokens_in, tokens_out=tokens_out,
            cache_read=cache_read, cache_write=cache_write,
            latency_s=round(latency_s, 2),
            stop_reason=stop_reason,
            block_types=block_types,
            text_chars=text_chars,
            thinking_blocks=thinking_blocks,
            thinking_chars=thinking_chars,
            prompt_chars=prompt_chars,
        )
        return text
    except urllib.error.HTTPError as e:
        body = e.read(300).decode("utf-8", errors="replace")
        if e.code == 429:
            print(f"  INFRA: HTTP 429 rate limit for {task_id} — caller should retry with backoff")
            raise RuntimeError(f"RATE_LIMIT:{e.code}:{body}") from e
        elif e.code >= 500:
            print(f"  INFRA: HTTP {e.code} server error for {task_id}")
            raise RuntimeError(f"API_SERVER_ERROR:{e.code}:{body}") from e
        else:
            print(f"  WARN: HTTP {e.code} for {task_id}: {body}")
            return None
    except TimeoutError:
        print(f"  INFRA: API read timed out after {api_timeout}s for {task_id}")
        raise RuntimeError(f"API_TIMEOUT:{api_timeout}s") from None
    except Exception as e:
        err = str(e)
        if "timed out" in err.lower() or "timeout" in err.lower():
            print(f"  INFRA: API read timed out for {task_id}: {err}")
            raise RuntimeError(f"API_TIMEOUT:{err}") from e
        print(f"  WARN: LLM call failed for {task_id}: {err}")
        return None


# ── UDCP Direct Caller ────────────────────────────────────────────────────────
# Implements: ADR-039 §5 — UDCP calls this instead of call_llm_via_magiclm.
# Constitutional basis: C-082 (compile gate enforced by caller, not here)
#
# MagicLLM's annotation/format gates are incompatible with UDCP's contracts:
#   Track 1 — scaffold already has # Implements: header; LLM fills markers only.
#   Track 2 — LLM returns ```python def ... ``` not a <file> block.
# UDCP's own compile gate is strictly stronger than MagicLLM's annotation gate.

_UDCP_MODEL_MAP: dict[str, str] = {
    "haiku":     "claude-haiku-4-5",
    "sonnet":    "claude-sonnet-4-6",
    "auto":      "claude-haiku-4-5",   # UDCP prompts are small — Haiku default
    "reasoning": "claude-sonnet-4-6",  # reasoning hint → Sonnet for complex fills
}

_UDCP_SYSTEM = (
    "You are a Python implementation assistant working inside the WAOOAW platform. "
    "Follow the user's instructions exactly. Return only what is asked — no extra commentary, "
    "no explanations outside the requested format.\n"
    "Python rules: SQLAlchemy — text() with named params only, never %s or ?. "
    "Timestamps — datetime.now(timezone.utc), never datetime.utcnow(). "
    "Exceptions — never swallow; use `raise X from err` in except blocks. "
    "Currency — PAISE (int), never float USD. "
    "Margin formula — floor / (1 - margin/100), never cost-plus."
)


def call_llm_for_udcp(
    task_id: str,
    prompt: str,
    model_hint: str = "auto",
    max_tokens: int = 8000,
    attempt: int = 1,
) -> str | None:
    """
    Direct Anthropic call for UDCP logic-fill and method-patch prompts.

    Differences from call_llm_via_magiclm:
      - Accepts haiku / sonnet / auto / reasoning model hints
      - No MagicLLM annotation/format validation gates (UDCP compile gate replaces them)
      - No PTR assembly (UDCP PTR gate already ran)
      - No goal register overhead per logic-fill call
      - Simple UDCP-specific system prompt
    """
    import json as _json
    import urllib.request as _urlreq

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(f"  WARN: ANTHROPIC_API_KEY not set — cannot call LLM for {task_id}")
        return None

    model_id = _UDCP_MODEL_MAP.get(model_hint, _UDCP_MODEL_MAP["auto"])
    payload: dict = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": 0,
        "system": _UDCP_SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }

    prompt_chars = len(_json.dumps(payload))
    print(f"  UDCP REQ: {task_id} attempt={attempt} model={model_id} "
          f"prompt={prompt_chars:,} chars max_tokens={max_tokens}")

    req = _urlreq.Request(
        "https://api.anthropic.com/v1/messages",
        data=_json.dumps(payload).encode(),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
            "content-type": "application/json",
        },
    )
    import time as _time
    timeout = max(60, min(300, (max_tokens // 50) * 3))
    t0 = _time.monotonic()
    try:
        with _urlreq.urlopen(req, timeout=timeout) as resp:
            result = _json.loads(resp.read())
    except Exception as exc:
        err = str(exc)
        if "timed out" in err.lower() or "timeout" in err.lower():
            print(f"  INFRA: UDCP API timed out for {task_id}: {err}")
            return None
        print(f"  WARN: UDCP LLM call failed for {task_id}: {err}")
        return None

    latency = _time.monotonic() - t0
    content = result.get("content", [])
    text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
    usage = result.get("usage", {})
    in_tok = usage.get("input_tokens", 0)
    out_tok = usage.get("output_tokens", 0)
    print(f"  UDCP RSP: {task_id} latency={latency:.1f}s "
          f"in={in_tok} out={out_tok} chars={len(text)}")
    _r_in = {"claude-sonnet-4-6": 0.24, "claude-haiku-4-5": 0.02}.get(model_id, 0.02)
    _r_out = {"claude-sonnet-4-6": 1.20, "claude-haiku-4-5": 0.10}.get(model_id, 0.10)
    _MONITOR_SIGNAL["file_costs"][task_id] = (
        _MONITOR_SIGNAL["file_costs"].get(task_id, 0.0)
        + round((in_tok / 1000) * _r_in + (out_tok / 1000) * _r_out, 4)
    )
    return text or None


# ── MagicLLM Bridge ────────────────────────────────────────────────────────────
# Implements: architecture/reference/magic-llm/architecture.md §4 Architecture
# Constitutional basis: C-059 (Evidence First), C-069 (Self-Improvement), C-077

def call_llm_via_magiclm(
    task_id: str,
    task_description: str,
    spec_content: str,
    constitutional_check: str,
    model_hint: str = "reasoning",
    max_tokens: int = 10000,
    attempt: int = 1,
    goal_id: str = "",
    ptr_snapshot: dict | None = None,
) -> str | None:
    """
    MagicLLM bridge — constitutionally governed LLM invocation.

    Adds vs. call_llm():
      ✓ Task complexity scoring → model selection (O-01: 91% cost reduction)
      ✓ Dynamic thinking budget (O-03)
      ✓ MagicLLM Decision Record committed to Goal Register (C-059 Evidence First)
      ✓ PTR 2.0 snapshot injected (includes .csproj packages — closes CS0246 gap)
      ✓ Stack-namespaced PTR (dotnet/python/terraform/typescript)
      ✓ Prompt caching: system prompt cached across retry attempts (C-077 cost reduction)

    Returns raw LLM response string (same format as call_llm()) or None.
    """
    if model_hint not in ("reasoning", "auto"):
        return None

    # Ensure both repo-root and scripts/ are importable in GitHub Actions and local script mode.
    repo_root_path = str(REPO_ROOT)
    scripts_path = str(REPO_ROOT / "scripts")
    if repo_root_path not in sys.path:
        sys.path.insert(0, repo_root_path)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)

    try:
        from scripts.magic_llm import MagicLLMPipeline, MagicLLMRequest, TaskCategory
        from scripts.goal_orchestrator.goal_register_github import make_goal_register_writer
    except ImportError:
        try:
            from magic_llm import MagicLLMPipeline, MagicLLMRequest, TaskCategory
            from goal_orchestrator.goal_register_github import make_goal_register_writer
        except ImportError as e:
            print(f"  WARN: MagicLLM not available ({e}) — falling back to _call_llm_direct()")
            return _call_llm_direct(task_id, task_description, spec_content,
                                    constitutional_check, model_hint, max_tokens, attempt)

    tid = task_id.lower()
    if "cct" in tid or "test" in tid or tid.endswith("-02c") or tid.endswith("-03c") or tid.endswith("-04c"):
        category = TaskCategory.TEST_GENERATION
    elif task_id.endswith("-skeleton") or "skeleton" in tid:
        category = TaskCategory.DESIGN_CONTRACTS
    elif "groom" in tid:
        # Groomer generates SubTaskDef metadata (design artifact), not source code
        category = TaskCategory.DESIGN_CONTRACTS
    else:
        category = TaskCategory.CODE_GENERATION

    if model_hint == "reasoning" and category == TaskCategory.CODE_GENERATION:
        category = TaskCategory.DEEP_REASONING

    effective_goal_id = goal_id or f"GOAL-{task_id.split('-')[0].upper()}"

    context_sections: list[str] = [spec_content]
    if constitutional_check:
        context_sections.append(f"## CONSTITUTIONAL REQUIREMENTS\n{constitutional_check}")

    if ptr_snapshot is None:
        try:
            try:
                from scripts.ptr_assembler import get_assembler
            except ImportError:
                from ptr_assembler import get_assembler
            assembler = get_assembler()
            full_ptr = assembler.assemble(scope=["src", "scripts"])
            task_ptr = assembler.extract_task_ptr(full_ptr, context_sections)
            stack = _TASK_STACK_MAP.get(task_id[:5], "dotnet")
            ptr_snapshot = task_ptr.get(stack, {})
        except Exception as e:
            print(f"  WARN: PTR 2.0 assembly failed ({e}) — using empty PTR")
            ptr_snapshot = {}

    request = MagicLLMRequest(
        goal_id=effective_goal_id,
        institution_id="INST-010",
        go_authorization_id=f"GOA-{effective_goal_id}-INST-010-{task_id}",
        task_category=category,
        task_description=task_description,
        context_sections=context_sections,
        ptr_snapshot=ptr_snapshot,
        expected_output_format="xml_file_blocks",
        execution_plan_reference=f"EP-{task_id}",
        previous_attempt_id=f"attempt-{attempt - 1}" if attempt > 1 else None,
        cascade_level=None,
        max_tokens=max_tokens,
    )

    writer = make_goal_register_writer()

    def _safe_write(record: dict) -> str:
        return writer.write_record(effective_goal_id, record)

    pipeline = MagicLLMPipeline(
        goal_register_writer=_safe_write,
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )

    try:
        response = pipeline.invoke(request)
    except RuntimeError:
        raise
    except Exception as e:
        print(f"  WARN: MagicLLM invocation error ({e}) — falling back to _call_llm_direct()")
        return _call_llm_direct(task_id, task_description, spec_content,
                                constitutional_check, model_hint, max_tokens, attempt)

    if response.status == "accepted":
        print(f"  ✓ MagicLLM: {response.model_version} · "
              f"complexity={response.parsed_artifacts.get('complexity', '?')} · "
              f"cost=₹{response.cost_inr:.4f} · attempt={attempt}")
        # Record per-task cost in monitor signal (consumed by G7 step summary)
        _MONITOR_SIGNAL["file_costs"][task_id] = (
            _MONITOR_SIGNAL["file_costs"].get(task_id, 0.0) + response.cost_inr
        )
        return response.raw_output
    else:
        print(f"  MagicLLM returned {response.status}: {response.failure_classification}")
        return None


def parse_llm_files(response: str) -> dict[str, str]:
    """
    Parse <file path="...">content</file> blocks from LLM response.
    Returns dict of {relative_path: content}.
    Enforces ADR-030 write boundary (ALLOWED_WRITE_ROOTS).
    """
    files: dict[str, str] = {}
    # IGNORECASE: LLMs sometimes emit <FILE path="..."> — FORMAT gate already uses IGNORECASE
    pattern = re.compile(r'<file\s+path=["\']([^"\']+)["\']>(.*?)</file>', re.DOTALL | re.IGNORECASE)
    for match in pattern.finditer(response):
        path = match.group(1).strip()
        content = match.group(2).strip()
        if not any(path.startswith(root) for root in ALLOWED_WRITE_ROOTS):
            print(f"  WARN: LLM attempted to write outside boundary: {path} — skipped")
            continue
        if "DESIGN_QUESTION:" in content:
            questions = re.findall(r"DESIGN_QUESTION: (.+)", content)
            for q in questions:
                print(f"  ⚠️  Design question in {path}: {q}")
        files[path] = content
    return files


def _inject_compliance_header(content: str, rel_path: str, task_id: str) -> str:
    """ADR-030 Amendment 2 Decision B: strip LLM-generated headers then prepend authoritative one.
    Ensures CCT-TR-01 always passes regardless of model context pressure (C-059).
    """
    ext = Path(rel_path).suffix.lower()
    if ext not in (".py", ".cs"):
        return content
    comment = "#" if ext == ".py" else "//"
    # Derive spec reference from task_id (e.g. "WC027-01a" → "WC-027")
    wc_num = ""
    import re as _re
    m = _re.match(r'(WC\d+)', task_id, _re.IGNORECASE)
    if m:
        raw = m.group(1).upper()           # e.g. "WC027"
        digits = _re.search(r'\d+', raw)
        wc_num = f"WC-{int(digits.group()):03d}" if digits else raw
    spec_ref = (
        f"work-contracts/{wc_num}-*.md §{task_id}" if wc_num
        else f"work-contracts/ §{task_id}" if task_id
        else "<spec-path> §<section>"
    )
    header = (
        f"{comment} Implements: {spec_ref}\n"
        f"{comment} constitutional_basis: C-059 (Implementation Traceability)\n"
    )
    # Strip any LLM-generated header lines to avoid duplication
    lines = content.splitlines(keepends=True)
    strip_prefixes = (f"{comment} Implements:", f"{comment} Constitutional basis:",
                      f"{comment} constitutional_basis:", f"{comment} ib_item:")
    while lines and lines[0].strip().startswith(strip_prefixes):
        lines.pop(0)
    return header + "".join(lines)


def write_llm_files(files: dict[str, str], task_id: str = "") -> list[str]:
    """Write parsed files to disk. Returns list of written relative paths."""
    written = []
    for rel_path, content in files.items():
        abs_path = REPO_ROOT / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        final_content = _inject_compliance_header(content, rel_path, task_id)
        abs_path.write_text(final_content, encoding="utf-8")
        written.append(rel_path)
        print(f"  Written: {rel_path} ({len(final_content)} chars)")
    return written


def validate_written_files(written: list[str]) -> tuple[bool, str]:
    """Run validation appropriate to file type. Returns (ok, error_text)."""
    from runner.git_ops import run as _run

    py_files = [f for f in written if f.endswith(".py")]
    cs_files = [f for f in written if f.endswith(".cs")]
    ok = True
    errors: list[str] = []

    for f in py_files:
        abs_f = str(REPO_ROOT / f)
        result = _run(["python3", "-m", "py_compile", abs_f], check=False, capture=True)
        if result.returncode != 0:
            msg = result.stderr.strip() or result.stdout.strip()
            print(f"  FAIL: {f} syntax error: {msg[:200]}")
            errors.append(f"{f}: {msg[:300]}")
            ok = False
        else:
            print(f"  ✅ Python syntax OK: {f}")

    if cs_files:
        csproj_dirs: set[str] = set()
        for f in cs_files:
            parts = Path(f).parts
            if len(parts) > 1:
                csproj_dirs.add(str(REPO_ROOT / parts[0] / parts[1]))
        for csproj_dir in csproj_dirs:
            csproj_files = list(Path(csproj_dir).glob("*.csproj")) if Path(csproj_dir).exists() else []
            if not csproj_files:
                msg = (f"No .csproj file found in {csproj_dir}. "
                       f"You MUST generate the .csproj in src/constitutional-engine/ (not any other directory). "
                       f"Write ALL files to src/constitutional-engine/ only.")
                print(f"  FAIL: {msg}")
                errors.append(msg)
                ok = False
                continue
            if len(csproj_files) > 1:
                canonical = [f for f in csproj_files if "-" in f.name]
                build_target = str(canonical[0]) if canonical else str(csproj_files[0])
                print(f"  WARN: {len(csproj_files)} .csproj found — building {Path(build_target).name}")
            else:
                build_target = str(csproj_files[0])
            result = _run(["dotnet", "build", build_target, "--nologo", "-v", "quiet"],
                         check=False, capture=True)
            if result.returncode != 0:
                build_output = (result.stdout.strip() or result.stderr.strip())[:600]
                print(f"  FAIL: dotnet build in {csproj_dir}:\n{build_output}")
                errors.append(f"dotnet build {csproj_dir}:\n{build_output}")
                ok = False
            else:
                print(f"  ✅ .NET build OK: {csproj_dir}")
    return ok, "\n".join(errors)
