# Implements: architecture/reference/magic-llm/architecture.md §4 Architecture
# Constitutional basis: C-059 (Evidence First), C-069 (Self-Improvement), C-077 (Cost Ceiling)
"""
MagicLLM Pipeline — Phase 1 implementation.

Phase 1 scope:
  Cat. 1-6 (engineering): Anthropic Claude Sonnet 4.6 via API (ADR-030 standard)
  Cat. 7-8 (semantic/research): NotImplemented — Phase 2 adds Gemini Vertex AI
  Cat. 9-13 (orchestration): NotImplemented — Phase 2 adds Gemini Vertex AI

Every invocation records a MagicLLMDecisionRecord BEFORE returning results (C-059).
"""
from __future__ import annotations
import json
import os
import re
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .types import (
    FailureClassification,
    MagicLLMDecisionRecord,
    MagicLLMRequest,
    MagicLLMResponse,
    QualityGate,
    TaskCategory,
)

_GEMINI_CATS = {
    TaskCategory.SEMANTIC_UNDERSTANDING,
    TaskCategory.RESEARCH_QUERY,
    TaskCategory.GOAL_UNDERSTANDING,
    TaskCategory.ROUTING_INTELLIGENCE,
    TaskCategory.JOURNEY_MONITOR,
    TaskCategory.RESEARCH_ORCHESTRATION,
    TaskCategory.DECISION_SYNTHESIS,
}

# ── Model routing (extends ADR-030 §Model Routing) ──────────────────────────────────
_ANTHROPIC_MODEL = "claude-sonnet-4-6"
_ANTHROPIC_HAIKU  = "claude-haiku-4-5"

# ADR-033: Gemini Flash for Cat. 7-13 (Orchestration + Semantic)
_GEMINI_FLASH  = "gemini-2.0-flash"
_GEMINI_REGION = "asia-south1"   # Mumbai — DPDPA India data residency

_ANTHROPIC_CATS = {
    TaskCategory.DEEP_REASONING,
    TaskCategory.CODE_GENERATION,
    TaskCategory.DESIGN_CONTRACTS,
    TaskCategory.REVIEW_EVALUATION,
    TaskCategory.DOCUMENTATION,
    TaskCategory.TEST_GENERATION,
}

# Cost estimates in INR (approximate, for C-077 tracking)
_COST_PER_1K_INPUT  = {
    "claude-sonnet-4-6": 0.24,
    "claude-haiku-20240307": 0.02,
    "gemini-2.0-flash": 0.007,   # ADR-033: 34× cheaper than Sonnet
}
_COST_PER_1K_OUTPUT = {
    "claude-sonnet-4-6": 1.20,
    "claude-haiku-20240307": 0.10,
    "gemini-2.0-flash": 0.021,
}
# Cached input costs 1/10th (O-02: prompt caching)
_COST_PER_1K_CACHED = {
    "claude-sonnet-4-6": 0.024,
    "claude-haiku-20240307": 0.002,
    "gemini-2.0-flash": 0.001,   # Gemini context caching (Phase 3)
}


def _task_complexity_score(request: "MagicLLMRequest") -> int:
    """
    O-01: Task complexity score determines model + thinking budget.
    Prevents over-spending Sonnet on boilerplate tasks.

    LOW  (0-39):  Haiku, no thinking  — boilerplate, scaffold, config
    MEDIUM (40-79): Haiku, no thinking  — standard patterns with light logic
    HIGH (80+):   Sonnet, thinking on — constitutional logic, CCT gates, security
    """
    score = 0
    score += len(request.context_sections) * 8          # more spec = more complex
    score += len(request.ptr_snapshot.get("types", {})) * 2  # more types = more context

    desc = (request.task_description or "").lower()
    # High-stakes markers
    if any(kw in desc for kw in ["cct", "constitutional", "evidence first", "emergency stop",
                                  "evaluator", "security", "c-041", "c-023", "c-001"]):
        score += 30
    # CCT gate in spec
    if any("cct" in s.lower() for s in request.context_sections):
        score += 25
    # Scaffold / boilerplate markers
    if any(kw in desc for kw in ["scaffold", "project", "csproj", "setup", "wiring",
                                  "skeleton", "hello world", "placeholder"]):
        score -= 20  # boilerplate penalty
    return max(0, score)


def _thinking_budget(complexity: int) -> int:
    """
    O-03: Dynamic thinking budget based on task complexity.
    Avoids burning 8K thinking tokens on simple tasks.
    """
    if complexity >= 80:
        return 8000   # HIGH: full budget
    if complexity >= 40:
        return 3000   # MEDIUM: reduced budget (saves ~60% of thinking cost)
    return 0          # LOW: no thinking (Haiku, no thinking mode)


class MagicLLMPipeline:
    """
    8-component constitutional AI execution pipeline.

    Component order: Task Classifier → Model Selector → Context Builder →
    Execution Contract → AI Execution Layer → Response Evaluator →
    [Retry Advisor] → Evidence Recorder

    Phase 1: Engineering categories only (Cat. 1-6).
    Phase 2: All 13 categories with Gemini Vertex AI for orchestration.
    """

    def __init__(
        self,
        goal_register_writer: Optional[Callable[[dict], str]] = None,
        api_key: Optional[str] = None,
        vertex_sa_key_json: Optional[str] = None,
    ) -> None:
        # Normalize writer: accept both (record) and (goal_id, record) signatures.
        # Fixes the 'write_record() missing 1 required positional argument: record' error.
        _raw_writer = goal_register_writer or self._default_file_writer
        def _normalized_writer(record: dict) -> str:
            try:
                return _raw_writer(record)  # new signature: (record,)
            except TypeError:
                try:
                    return _raw_writer(record.get("goal_id", ""), record)  # old: (goal_id, record)
                except Exception:
                    return ""
        self._write_record = _normalized_writer
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        # ADR-033: Gemini Vertex AI SA key (JSON string)
        self._vertex_sa_key_json = (
            vertex_sa_key_json
            or os.environ.get("GOOGLE_VERTEX_SA_KEY", "")
        )
        # Token cache: (access_token, expiry_timestamp)
        self._vertex_token_cache: Optional[tuple[str, float]] = None

    # ── Public API ───────────────────────────────────────────────────────────

    def invoke(self, request: MagicLLMRequest) -> MagicLLMResponse:
        """
        Single entry point for all MagicLLM invocations.
        Records MagicLLMDecisionRecord to Goal Register BEFORE returning (C-059).
        Cat. 1-6: Anthropic Claude   (ADR-030)
        Cat. 7-13: Gemini Flash on Vertex AI asia-south1  (ADR-033)
        """
        # ① Task Classifier — route to correct AI Execution Layer
        use_gemini = request.task_category in _GEMINI_CATS

        # ② Model Selector (O-01: task complexity scoring)
        model, temperature = self._select_model(request.task_category, request)
        complexity = _task_complexity_score(request)

        # ③ Context Builder
        prompt = self._build_prompt(request)

        # ④ Execution Contract
        max_tokens = request.max_tokens
        # O-03: thinking budget (Anthropic only — Gemini reasons internally)
        thinking_budget = _thinking_budget(complexity) if not use_gemini else 0
        use_thinking = thinking_budget > 0 and model == _ANTHROPIC_MODEL

        # ⑤ AI Execution Layer — Anthropic or Gemini
        if use_gemini:
            raw_response, in_tok, out_tok = self._call_gemini(
                prompt=prompt,
                max_tokens=max_tokens,
            )
            model_provider = "google"
        else:
            raw_response, in_tok, out_tok = self._call_anthropic(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                use_thinking=use_thinking,
                thinking_budget=thinking_budget,
            )
            model_provider = "anthropic"

        cost = self._estimate_cost(model, in_tok, out_tok)

        # ⑥ Response Evaluator
        status, gates, failure_class, failure_detail = self._evaluate(
            raw_response, request
        )

        response = MagicLLMResponse(
            request_id=str(uuid.uuid4()),
            goal_id=request.goal_id,
            institution_id=request.institution_id,
            task_category=request.task_category,
            status=status,
            raw_output=raw_response or "",
            parsed_artifacts=self._parse_artifacts(raw_response, request.expected_output_format),
            gates_evaluated=gates,
            failure_classification=failure_class,
            failure_detail=failure_detail,
            model_provider=model_provider,
            model_version=model,
            temperature=temperature,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_inr=cost,
            attempt_number=1 if not request.previous_attempt_id else 2,
        )

        # ⑧ Evidence Recorder — BEFORE returning (C-059 Evidence First)
        decision_record = MagicLLMDecisionRecord(
            institution_id="INST-008",
            invoked_by=request.institution_id,
            goal_id=request.goal_id,
            record_id=f"MDR-{request.goal_id}-{request.institution_id}-{int(time.time())}",
            task_category=request.task_category,
            model_provider=model_provider,
            model_version=model,
            temperature=temperature,
            token_allocation=f"{in_tok}/{out_tok}",
            context_strategy=(
                f"{len(request.context_sections)} sections, PTR={'yes' if request.ptr_snapshot else 'no'}, "
                f"complexity={complexity}, thinking_budget={thinking_budget}"
            ),
            gates_evaluated={k: ("PASS" if v else "FAIL") for k, v in gates.items()},
            retry_count=0 if not request.previous_attempt_id else 1,
            cost_incurred_inr=cost,
            cascade_level=request.cascade_level,
        )
        self._write_record(decision_record.to_dict())

        return response

    def retry_with_enhanced_context(
        self,
        goal_id: str,
        failure_evidence: dict,
        attempt: int,
        original_request: Optional[MagicLLMRequest] = None,
    ) -> MagicLLMResponse:
        """L1 Cascade retry — enhanced context from RetryAdvisor."""
        if original_request is None:
            raise ValueError("original_request required for retry")

        correction = self._classify_retry(failure_evidence)
        enhanced_sections = list(original_request.context_sections) + [
            f"## RETRY CORRECTION (attempt {attempt})\n{correction}"
        ]
        retry_req = MagicLLMRequest(
            goal_id=goal_id,
            institution_id=original_request.institution_id,
            go_authorization_id=original_request.go_authorization_id,
            task_category=original_request.task_category,
            task_description=original_request.task_description,
            context_sections=enhanced_sections,
            ptr_snapshot=original_request.ptr_snapshot,
            expected_output_format=original_request.expected_output_format,
            execution_plan_reference=original_request.execution_plan_reference,
            previous_attempt_id=str(uuid.uuid4()),
            cascade_level=1,
        )
        return self.invoke(retry_req)

    def retry_with_research_context(
        self,
        goal_id: str,
        research_record: Any,  # ResearchRecord
        attempt: int,
        original_request: Optional[MagicLLMRequest] = None,
    ) -> MagicLLMResponse:
        """L2 Cascade retry — research findings injected into context."""
        if original_request is None:
            raise ValueError("original_request required for research retry")

        research_section = (
            "## INDUSTRY RESEARCH FINDINGS (Level 2 Remediation)\n"
            + "\n".join(research_record.recommendations[:3])
        )
        enhanced_sections = list(original_request.context_sections) + [research_section]
        retry_req = MagicLLMRequest(
            goal_id=goal_id,
            institution_id=original_request.institution_id,
            go_authorization_id=original_request.go_authorization_id,
            task_category=original_request.task_category,
            task_description=original_request.task_description,
            context_sections=enhanced_sections,
            ptr_snapshot=original_request.ptr_snapshot,
            expected_output_format=original_request.expected_output_format,
            execution_plan_reference=original_request.execution_plan_reference,
            previous_attempt_id=str(uuid.uuid4()),
            cascade_level=2,
            research_record_id=research_record.record_id,
        )
        return self.invoke(retry_req)

    # ── Private: Model Selector (②) ──────────────────────────────────────────

    def _select_model(self, category: TaskCategory, request: "MagicLLMRequest" = None) -> tuple[str, float]:
        """O-01: Returns (model_name, temperature) using task complexity scoring.
        ADR-033: Cat. 7-13 always use Gemini Flash.
        Industry Item 10: skeleton phase → Haiku (10x cheaper); logic/test → Sonnet.
        """
        # ADR-033: Gemini for orchestration + semantic categories
        if category in _GEMINI_CATS:
            return _GEMINI_FLASH, 0.1

        # Anthropic for engineering categories (Cat. 1-6)
        if category in (TaskCategory.CODE_GENERATION, TaskCategory.TEST_GENERATION,
                        TaskCategory.DEEP_REASONING, TaskCategory.DESIGN_CONTRACTS):
            if request is not None:
                desc = (request.task_description or "").lower()
                is_skeleton = "skeleton" in desc or "SKELETON PHASE" in " ".join(request.context_sections)

                # DEEP_REASONING = explicit model_hint="reasoning" from task — always Sonnet.
                # GoalExecutor packs everything into one context_sections entry, so complexity
                # scoring returns ~8 (1 section × 8) regardless of actual complexity.
                # "reasoning" is an explicit override — skip scoring, use Sonnet directly.
                if category == TaskCategory.DEEP_REASONING and not is_skeleton:
                    return _ANTHROPIC_MODEL, 0.0

                complexity = _task_complexity_score(request)
                # Cost-aware tiering: SKELETON phase → always Haiku (signatures only, no reasoning needed)
                # LOGIC/TEST phase → Sonnet when complexity is high, Haiku otherwise
                if is_skeleton:
                    return _ANTHROPIC_HAIKU, 0.0  # skeleton: cheap model always
                if complexity >= 80:
                    return _ANTHROPIC_MODEL, 0.0  # HIGH complexity → Sonnet
                return _ANTHROPIC_HAIKU, 0.0      # LOW/MEDIUM → Haiku (10x cheaper)
            return _ANTHROPIC_MODEL, 0.0           # fallback if no request
        return _ANTHROPIC_HAIKU, 0.0

    # ── Private: Context Builder (③) ─────────────────────────────────────────

    def _build_prompt(self, request: MagicLLMRequest) -> str:
        """Assembles context sections + PTR + constitutional obligations.
        ADR-033: Cat. 7-13 use a different preamble (no code annotation requirement).
        """
        parts: list[str] = []

        if request.task_category in _GEMINI_CATS:
            # Orchestration/semantic preamble — no annotation or file block requirement
            parts.append(
                "## CONSTITUTIONAL OBLIGATIONS\n"
                "You are the WAOOAW Goal Orchestrator (INST-013). "
                "Operate under C-001 (Evidence First), C-059 (Traceability), C-007 (Append-Only). "
                "Produce structured output as instructed. Do not hallucinate institution IDs or claim IDs."
            )
        else:
            # Engineering preamble — code annotation required
            parts.append(
                "## CONSTITUTIONAL OBLIGATIONS\n"
                "Every file you produce MUST begin with:\n"
                "# Implements: <spec-path> §<section>\n"
                "# Constitutional basis: C-NNN (<claim name>)\n"
                "Output format: <file path=\"relative/path/to/file.ext\">...content...</file>\n"
            )

        # Platform Type Registry injection (for code tasks)
        if request.ptr_snapshot:
            ptr_lines = [f"  {k}: {v}" for k, v in list(request.ptr_snapshot.items())[:30]]
            parts.append("## PLATFORM TYPE REGISTRY (compiled types)\n" + "\n".join(ptr_lines))

        # Industry Item 12: Forbidden API patterns — prevent LLM from inventing non-existent methods.
        _FORBIDDEN_APIS = (
            "## FORBIDDEN API PATTERNS (do NOT use — these do not exist)\n"
            "  ❌ FIRST LINE RULE: every .cs file MUST start with // or using — NEVER ## or markdown (causes CS1024)\n"
            "  ❌ .AsTask() on Task<T>  — Task<T> IS already awaitable, just use 'await task;'\n"
            "  ❌ .TryGetValue() on string/EvaluationContext — use ctx.GetParameter('key')\n"
            "  ❌ .TryGetValue() on proto fields — proto fields are properties, not dictionaries\n"
            "  ❌ BudgetRemainingInrPaise — does not exist on EvaluationContext\n"
            "  ❌ ValidationDecision.Authorized/Denied/Permit — use Allow/Deny/Escalate\n"
            "  ❌ new ConstitutionalDbContext() — always inject via constructor DI\n"
            "  ❌ Mixed named+positional args: e.g. new Svc(a, b, logger: x) — use all positional"
        )
        parts.append(_FORBIDDEN_APIS)

        # Spec sections
        for i, section in enumerate(request.context_sections):
            parts.append(f"## CONTEXT SECTION {i + 1}\n{section}")

        # Task
        parts.append(f"## TASK\n{request.task_description}")

        return "\n\n---\n\n".join(parts)

    # ── Private: AI Execution Layer — Gemini (ADR-033) ───────────────────────

    def _get_vertex_token(self) -> str:
        """Exchange SA key for Vertex AI access token (OAuth2 JWT Bearer — RFC 7523).
        Token cached in-memory for 55 minutes (expires at 60, refreshed early).
        """
        import time as _time
        now = _time.time()

        # Return cached token if still valid
        if self._vertex_token_cache is not None:
            token, expiry = self._vertex_token_cache
            if now < expiry:
                return token

        if not self._vertex_sa_key_json:
            raise RuntimeError(
                "GOOGLE_VERTEX_SA_KEY not set — cannot call Gemini. "
                "Add the GCP service account JSON to Azure Key Vault (ADR-033)."
            )

        sa = json.loads(self._vertex_sa_key_json)
        iat = int(now)
        exp = iat + 3600

        try:
            import jwt as _jwt  # PyJWT
            payload = {
                "iss": sa["client_email"],
                "scope": "https://www.googleapis.com/auth/cloud-platform",
                "aud": "https://oauth2.googleapis.com/token",
                "exp": exp,
                "iat": iat,
            }
            signed_jwt = _jwt.encode(payload, sa["private_key"], algorithm="RS256")
        except Exception as exc:
            raise RuntimeError(f"Failed to sign SA JWT: {exc}") from exc

        # Exchange JWT for access token
        body = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": signed_jwt,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Token exchange failed: {exc}") from exc

        access_token: str = token_data["access_token"]
        # Cache for 55 minutes (5 min before expiry)
        self._vertex_token_cache = (access_token, now + 55 * 60)
        return access_token

    def _call_gemini(
        self,
        prompt: str,
        max_tokens: int,
    ) -> tuple[str | None, int, int]:
        """Vertex AI Gemini REST API call — asia-south1 (Mumbai, DPDPA compliant).
        ADR-033: Cat. 7-13 orchestration + semantic categories.
        """
        if not self._vertex_sa_key_json:
            print("  [MagicLLM] GOOGLE_VERTEX_SA_KEY not set — Gemini call skipped")
            return None, 0, 0

        try:
            sa = json.loads(self._vertex_sa_key_json)
            project_id: str = sa["project_id"]
            token = self._get_vertex_token()
        except Exception as exc:
            print(f"  [MagicLLM] Gemini auth failed: {exc}")
            return None, 0, 0

        url = (
            f"https://{_GEMINI_REGION}-aiplatform.googleapis.com/v1/projects/{project_id}"
            f"/locations/{_GEMINI_REGION}/publishers/google/models/{_GEMINI_FLASH}:generateContent"
        )
        body = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.1,
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            print(f"  [MagicLLM] Gemini API call failed: {exc}")
            return None, 0, 0

        candidates = data.get("candidates", [])
        text = ""
        if candidates:
            parts_list = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts_list)

        usage = data.get("usageMetadata", {})
        in_tok: int = usage.get("promptTokenCount", 0)
        out_tok: int = usage.get("candidatesTokenCount", 0)
        return text or None, in_tok, out_tok

    # ── Private: AI Execution Layer — Anthropic (⑤) ──────────────────────────

    def _call_anthropic(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        use_thinking: bool,
        thinking_budget: int = 8000,
    ) -> tuple[str | None, int, int]:
        """Direct Anthropic API call — O-03: dynamic thinking_budget."""
        if not self._api_key:
            return None, 0, 0

        # O-03: dynamic budget — only add overhead when thinking is actually enabled
        effective_max = (max_tokens + thinking_budget) if use_thinking else max_tokens

        body: dict[str, Any] = {
            "model": model,
            "max_tokens": effective_max,
            "messages": [{"role": "user", "content": prompt}],
        }
        if use_thinking:
            body["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "anthropic-beta": "interleaved-thinking-2025-05-14",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            print(f"  [MagicLLM] API call failed: {exc}")
            return None, 0, 0

        in_tok  = data.get("usage", {}).get("input_tokens", 0)
        out_tok = data.get("usage", {}).get("output_tokens", 0)
        text_blocks = [
            b["text"] for b in data.get("content", []) if b.get("type") == "text"
        ]
        return "\n".join(text_blocks) if text_blocks else None, in_tok, out_tok

    # ── Private: Response Evaluator (⑥) ──────────────────────────────────────

    def _evaluate(
        self,
        raw: str | None,
        request: MagicLLMRequest,
    ) -> tuple[str, dict[str, bool], Optional[FailureClassification], Optional[str]]:
        """Runs quality gates. Returns (status, gates_dict, failure_class, detail)."""
        gates: dict[str, bool] = {}

        if not raw:
            gates[QualityGate.FORMAT] = False
            return "escalate", gates, FailureClassification.FORMAT_FAILURE, "empty response"

        # Format gate
        if request.expected_output_format == "xml_file_blocks":
            has_files = bool(re.search(r'<file\s+path=', raw))
            gates[QualityGate.FORMAT] = has_files
            if not has_files:
                return "retry_needed", gates, FailureClassification.FORMAT_FAILURE, "no <file> blocks found"
        elif request.expected_output_format == "json":
            try:
                json.loads(raw)
                gates[QualityGate.FORMAT] = True
            except json.JSONDecodeError as e:
                gates[QualityGate.FORMAT] = False
                return "retry_needed", gates, FailureClassification.SCHEMA_VIOLATION, str(e)
        else:
            gates[QualityGate.FORMAT] = bool(raw.strip())

        # Annotation gate (C-073) — for code tasks only (Cat. 1-6, stack-aware)
        # ADR-033: Cat. 7-13 produce prose/JSON, not source files — no annotation required
        if request.task_category in (TaskCategory.CODE_GENERATION, TaskCategory.TEST_GENERATION):
            # Python/Terraform/CSS: # Implements:  |  C#/JS/TS: // Implements:
            has_implements = ("# Implements:" in raw) or ("// Implements:" in raw)
            gates[QualityGate.ANNOTATION] = has_implements
            if not has_implements:
                return "retry_needed", gates, FailureClassification.ANNOTATION_MISSING, \
                       "missing # Implements: or // Implements: header (C-073)"

        return "accepted", gates, None, None

    # ── Private: Retry Advisor (⑦) ───────────────────────────────────────────

    def _classify_retry(self, failure_evidence: dict) -> str:
        """Maps failure evidence to targeted correction text."""
        fc = failure_evidence.get("failure_classification", "")
        if fc == FailureClassification.CS1061_MISSING_PROPERTY:
            prop = failure_evidence.get("detail", "unknown property")
            return (
                f"CS1061 Fix: The property '{prop}' does not exist on that type. "
                "Consult the Platform Type Registry above for the exact available properties. "
                "Do NOT call TryGetValue() on a non-dictionary type."
            )
        if fc == FailureClassification.CS0246_MISSING_TYPE:
            return "CS0246 Fix: The referenced type is not imported. Add the correct using statement from the PTR above."
        if fc == FailureClassification.ANNOTATION_MISSING:
            return "C-073 Fix: Every file must begin with:\n# Implements: <spec-path> §<section>\n# Constitutional basis: C-NNN"
        if fc == FailureClassification.FORMAT_FAILURE:
            return "FORMAT Fix: Respond with XML file blocks only: <file path=\"...\">...content...</file>"
        return f"GENERIC Fix: Previous attempt failed with: {fc}. Review spec sections carefully."

    # ── Private: Artifact Parser ──────────────────────────────────────────────

    def _parse_artifacts(self, raw: str | None, fmt: str) -> dict[str, Any]:
        if not raw:
            return {}
        if fmt == "xml_file_blocks":
            files: dict[str, str] = {}
            for m in re.finditer(r'<file\s+path="([^"]+)">(.*?)</file>', raw, re.DOTALL):
                files[m.group(1)] = m.group(2).strip()
            return {"files": files}
        if fmt == "json":
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw}
        return {"prose": raw}

    # ── Private: Cost Estimator ───────────────────────────────────────────────

    def _estimate_cost(self, model: str, in_tok: int, out_tok: int) -> float:
        """Estimates cost in INR for C-077 tracking."""
        r_in  = _COST_PER_1K_INPUT.get(model, 0)
        r_out = _COST_PER_1K_OUTPUT.get(model, 0)
        return round((int(in_tok) / 1000) * r_in + (int(out_tok) / 1000) * r_out, 4)

    # ── Private: Default file-based Goal Register writer (Phase 1) ───────────

    @staticmethod
    def _default_file_writer(record: dict) -> str:
        """Phase 1: writes Decision Records to a JSON-lines file.
        Phase 2: replaced by PostgreSQL constitutional.goal_register insert.
        """
        register_path = Path(__file__).parent.parent.parent / "goals" / "goal_register.jsonl"
        register_path.parent.mkdir(parents=True, exist_ok=True)
        with register_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return record.get("record_id", "")
