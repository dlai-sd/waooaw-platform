# Work Contract 020 — GOAL-PLATFORM-REGISTRY: PL-EA-01 Manifests + Skeletons

**Office:** Enterprise Architect (INST-004)
**Sprint:** 020
**Goal:** GOAL-PLATFORM-REGISTRY
**Sprint Label:** PL-EA-01
**task_type:** SKELETON
**model_hint:** reasoning
**Sequencing:** After WC-016 complete. Before WC-022 (pipeline upgrades need skeletons).
**Constitutional Basis:** C-059, C-095, ADR-036

## Tasks

### WC020-01 — CE manifest + skeleton
Extract CE public interface → ce.yaml + src/constitutional-engine/skeleton/
model_hint: reasoning

### WC020-02 — BP manifest + skeleton
Extract BP public interface → bp.yaml + src/business-platform/skeleton/
model_hint: reasoning

### WC020-03 — PR manifest + skeleton
Extract PR public interface → pr.yaml + src/professional-runtime/skeleton/
model_hint: reasoning

### WC020-04 — AIR manifest + skeleton
Extract AIR public interface → air.yaml + src/ai-runtime/skeleton/
model_hint: reasoning

### WC020-05 — WBE manifest + skeleton
Produce wbe.yaml + src/billing-engine/skeleton/ from GOAL-004 D-07
model_hint: reasoning

## Definition of Done
- All 5 manifest files exist in architecture/reference/components/manifest/
- All 5 skeleton/ directories exist and every file passes syntax check
- Compile gate: python3 -c "import ast; [ast.parse(f.read_text()) for f in Path('src/ai-runtime/skeleton').rglob('*.py')]"
