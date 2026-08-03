# Proposed Fix: UDCP Contract Discipline (Option A)

**Session:** 2026-08-03  
**RCA run:** 30789462673 — WC027-01aa MISSING_DELIVERABLE, all dependents SKIPPED  
**Root cause:** `detect_track()` and `generate_tis()` derive file targets from scope_text regex,
independent of `output_files`. When test files exist but src files are absent (post clean-slate),
MIXED track + `skip_existing=True` → `files_written=[]` with `success=True`.  
**Fix:** Thread `output_files` (SubTaskDef, the authoritative sprint contract) through every UDCP
layer as `required_output_files`. Groomer uses it directly instead of re-deriving from scope_text.

---

## Files to Change

### 1. `scripts/runner/udcp_grooming_engine.py`

#### `detect_track` — replace scope_text param with required_output_files

```python
# BEFORE (line 91):
def detect_track(self, scope_text: str) -> str:
    file_paths = _FILE_PATH_RE.findall(scope_text)
    if not file_paths:
        return "GREENFIELD"
    existing = [
        fp for fp in file_paths
        if (self.repo_root / fp).is_file()
        and "WAOOAW_LOGIC_FILLER_START" not in (self.repo_root / fp).read_text(encoding="utf-8", errors="replace")
    ]
    if not existing:
        return "GREENFIELD"
    if len(existing) == len(file_paths):
        return "DIFFERENTIAL"
    return "MIXED"

# AFTER:
def detect_track(self, required_output_files: list[str]) -> str:
    if not required_output_files:
        return "GREENFIELD"
    existing = [
        fp for fp in required_output_files
        if (self.repo_root / fp).is_file()
        and "WAOOAW_LOGIC_FILLER_START" not in (self.repo_root / fp).read_text(encoding="utf-8", errors="replace")
    ]
    if not existing:
        return "GREENFIELD"
    if len(existing) == len(required_output_files):
        return "DIFFERENTIAL"
    return "MIXED"
```

#### `generate_tis` — add required_output_files, use it for target_artifacts

```python
# BEFORE (line 44):
def generate_tis(self, task_id: str, scope_text: str, sprint_id: str = "") -> dict[str, Any]:
    artifacts = self._extract_artifacts(scope_text, track=1)
    return {"sprint_id": sprint_id, "task_id": task_id,
            "pipeline_track": "GREENFIELD", "target_artifacts": artifacts}

# AFTER:
def generate_tis(
    self,
    task_id: str,
    scope_text: str,
    sprint_id: str = "",
    required_output_files: list[str] | None = None,
) -> dict[str, Any]:
    if required_output_files:
        # Contract-driven: build artifacts from declared output_files, not scope_text regex
        artifacts = [
            {
                "file_path": fp,
                "imports": self._extract_imports(scope_text, fp),
                "interfaces": self._extract_interfaces(scope_text, fp),
            }
            for fp in required_output_files
        ]
    else:
        # Fallback: legacy regex extraction (for callers without output_files)
        artifacts = self._extract_artifacts(scope_text, track=1)
    return {"sprint_id": sprint_id, "task_id": task_id,
            "pipeline_track": "GREENFIELD", "target_artifacts": artifacts}
```

#### `generate_tmd` — add required_output_files, use it for impacted_artifacts

```python
# BEFORE (line 62):
def generate_tmd(self, task_id: str, scope_text: str, sprint_id: str = "") -> dict[str, Any]:
    file_paths = _FILE_PATH_RE.findall(scope_text)
    artifacts = [...]

# AFTER:
def generate_tmd(
    self,
    task_id: str,
    scope_text: str,
    sprint_id: str = "",
    required_output_files: list[str] | None = None,
) -> dict[str, Any]:
    file_paths = required_output_files if required_output_files else _FILE_PATH_RE.findall(scope_text)
    artifacts = []
    for fp in file_paths:
        class_match = _IMPLEMENTS_RE.search(scope_text)
        target_class = class_match.group(1) if class_match else None
        artifacts.append({
            "file_path": fp,
            "target_class": target_class,
            "target_methods": self._extract_method_names(scope_text, target_class),
        })
    return {"sprint_id": sprint_id, "task_id": task_id,
            "pipeline_track": "DIFFERENTIAL", "impacted_artifacts": artifacts}
```

---

### 2. `scripts/runner/udcp_orchestrator.py`

#### `UDCPOrchestrator.execute_task` — add required_output_files

```python
# BEFORE (line 153):
def execute_task(
    self,
    task_id: str,
    scope_text: str,
    sprint_id: str = "",
    model_hint: str = "reasoning",
    max_tokens: int = 8000,
) -> TaskResult:
    track = self.groom.detect_track(scope_text)
    if track == "GREENFIELD":
        return self._run_track1(task_id, scope_text, sprint_id, model_hint, max_tokens)
    elif track == "DIFFERENTIAL":
        return self._run_track2(task_id, scope_text, sprint_id, model_hint, max_tokens)
    else:
        r1 = self._run_track1(task_id, scope_text, sprint_id, model_hint, max_tokens, skip_existing=True)
        ...

# AFTER:
def execute_task(
    self,
    task_id: str,
    scope_text: str,
    sprint_id: str = "",
    model_hint: str = "reasoning",
    max_tokens: int = 8000,
    required_output_files: list[str] | None = None,
) -> TaskResult:
    track = self.groom.detect_track(required_output_files or [])
    if track == "GREENFIELD":
        return self._run_track1(task_id, scope_text, sprint_id, model_hint, max_tokens,
                                required_output_files=required_output_files)
    elif track == "DIFFERENTIAL":
        return self._run_track2(task_id, scope_text, sprint_id, model_hint, max_tokens,
                                required_output_files=required_output_files)
    else:
        r1 = self._run_track1(task_id, scope_text, sprint_id, model_hint, max_tokens,
                              skip_existing=True, required_output_files=required_output_files)
        if not r1.success:
            return r1
        r2 = self._run_track2(task_id, scope_text, sprint_id, model_hint, max_tokens,
                               required_output_files=required_output_files)
        if not r2.success and r2.error_type != "GROOMING_ERROR":
            return r2
        return TaskResult(success=True, track="MIXED",
                          files_written=r1.files_written + r2.files_written)
```

#### `_run_track1` — add required_output_files, pass to generate_tis + skip_existing filter

```python
# BEFORE (line 188):
def _run_track1(self, task_id, scope_text, sprint_id, model_hint, max_tokens,
                skip_existing: bool = False) -> TaskResult:
    try:
        tis = self.groom.generate_tis(task_id, scope_text, sprint_id)
    ...
    if skip_existing:
        tis["target_artifacts"] = [
            a for a in tis["target_artifacts"]
            if not (self.repo_root / a["file_path"]).is_file()
        ]

# AFTER:
def _run_track1(self, task_id, scope_text, sprint_id, model_hint, max_tokens,
                skip_existing: bool = False,
                required_output_files: list[str] | None = None) -> TaskResult:
    try:
        tis = self.groom.generate_tis(task_id, scope_text, sprint_id,
                                      required_output_files=required_output_files)
    ...
    if skip_existing:
        tis["target_artifacts"] = [
            a for a in tis["target_artifacts"]
            if not (self.repo_root / a["file_path"]).is_file()
        ]
        if not tis["target_artifacts"]:
            return TaskResult(success=True, track="MIXED", files_written=[])
```

#### `_run_track2` — add required_output_files, pass to generate_tmd

```python
# Find _run_track2 (line ~352) and add the same param + forward to generate_tmd:
def _run_track2(self, task_id, scope_text, sprint_id, model_hint, max_tokens,
                required_output_files: list[str] | None = None) -> TaskResult:
    try:
        tmd = self.groom.generate_tmd(task_id, scope_text, sprint_id,
                                      required_output_files=required_output_files)
    ...
```

---

### 3. `scripts/runner/task_executor.py`

#### `execute_with_udcp` — add required_output_files, pass to orchestrator

```python
# BEFORE (line 362):
def execute_with_udcp(
    task_id: str, scope_text: str, sprint_id: str = "",
    model_hint: str = "reasoning", max_tokens: int = 8000,
) -> tuple[bool, list[str]]:
    ...
    result = orchestrator.execute_task(
        task_id=task_id, scope_text=scope_text, sprint_id=sprint_id,
        model_hint=model_hint, max_tokens=max_tokens,
    )

# AFTER:
def execute_with_udcp(
    task_id: str, scope_text: str, sprint_id: str = "",
    model_hint: str = "reasoning", max_tokens: int = 8000,
    required_output_files: list[str] | None = None,
) -> tuple[bool, list[str]]:
    ...
    result = orchestrator.execute_task(
        task_id=task_id, scope_text=scope_text, sprint_id=sprint_id,
        model_hint=model_hint, max_tokens=max_tokens,
        required_output_files=required_output_files,
    )
```

---

### 4. `scripts/task_decomposer.py`

#### UDCP call site — pass st.output_files as required_output_files

```python
# BEFORE (~line 1251):
success, udcp_files_written = execute_with_udcp(
    task_id=st.id,
    scope_text=scope_text,
    sprint_id=task_id,
    model_hint=st.model_hint,
    max_tokens=st.max_tokens,
)

# AFTER:
success, udcp_files_written = execute_with_udcp(
    task_id=st.id,
    scope_text=scope_text,
    sprint_id=task_id,
    model_hint=st.model_hint,
    max_tokens=st.max_tokens,
    required_output_files=st.output_files or None,
)
```

---

## Tests to Update

File: `tests/pipeline/test_task_decomposer.py` — `TestUDCPDispatch` class  
All `fake_udcp` mocks already return `(True, [])` / `(False, [])` (fixed in P0).  
No mock signature change needed — `required_output_files` is keyword-only and optional.

File: `tests/runner/test_udcp_grooming_engine.py` (if exists)  
Update `detect_track` test calls:
```python
# BEFORE: engine.detect_track(scope_text_with_file_paths)
# AFTER:  engine.detect_track(["src/billing-engine/markup/models.py"])
```

New test to add in `TestUDCPDispatch`:
```python
def test_udcp_uses_output_files_not_scope_text_for_track_detection(self, tmp_path):
    """UDCP must not write files outside output_files even if scope_text mentions more paths."""
    # scope_text mentions test files that exist; output_files only has src files (absent)
    # Expected: GREENFIELD (not MIXED), scaffold src files
```

---

## Expected Outcome After Implementation

```
WC027-01aa: detect_track([models.py, bundle_engine.py]) → GREENFIELD (neither exists)
            Track 1 scaffolds both → files_written=[models.py, bundle_engine.py]
            Compile gate: checks models.py + bundle_engine.py → PASS

WC027-01ab: detect_track([models.py, bundle_engine.py]) → DIFFERENTIAL (both now exist)
            Track 2 logic-fills both → files_written=[models.py, bundle_engine.py]
            Compile gate → PASS

WC027-02a:  detect_track([test_markup.py]) → DIFFERENTIAL (test_markup.py exists)
            Track 2 patches test_markup.py → files_written=[test_markup.py]
            Compile gate: checks only test_markup.py → PASS (pre-existing B904 not in scope)
```

Sprint WC-027 completes. Branch merges. WC-028 starts.

---

## Implementation Order

1. `udcp_grooming_engine.py` — `detect_track` + `generate_tis` + `generate_tmd`
2. `udcp_orchestrator.py` — `execute_task` + `_run_track1` + `_run_track2`
3. `task_executor.py` — `execute_with_udcp`
4. `task_decomposer.py` — call site (one line)
5. Update grooming engine tests
6. `py_compile` + `ruff check` + `pytest tests/runner/ tests/pipeline/ -q`
7. Commit: `fix(udcp): Option A — contract-driven track detection and TIS generation`
8. Push → trigger sprint run

Estimated changes: ~80 lines across 4 files. All additive (new optional params with fallback).
No breaking changes to existing callers without output_files.
