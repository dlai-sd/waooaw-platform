# Canonical Patterns — WC-015 (python)

**Status:** CANDIDATE — awaiting Constitutional Analyst review  

**Source sprint:** WC-015  

**Extracted:** 2026-07-30  

**Confidence:** 0.5 (CANDIDATE) — promoted to 1.0 after CA review


---

### PYTHON-FASTAPI-WC015-emergency_stop.py

**Status:** CANDIDATE  
**Category:** fastapi-router  
**Confidence:** 0.5  
**Source:** `src/professional-runtime/routers/emergency_stop.py` (from GOAL-WC015)  
**Created:** 2026-07-30

FastAPI router pattern from WC-015: async routes with dependency injection.

```
from fastapi import APIRouter, Depends

router = APIRouter(prefix='/endpoint', tags=['tag'])

@router.get('/{id}')
async def get_item(id: str, db: AsyncSession = Depends(get_db)):
    # Implementation
    pass
```


---

### PYTHON-FASTAPI-WC015-sessions.py

**Status:** CANDIDATE  
**Category:** fastapi-router  
**Confidence:** 0.5  
**Source:** `src/professional-runtime/routers/sessions.py` (from GOAL-WC015)  
**Created:** 2026-07-30

FastAPI router pattern from WC-015: async routes with dependency injection.

```
from fastapi import APIRouter, Depends

router = APIRouter(prefix='/endpoint', tags=['tag'])

@router.get('/{id}')
async def get_item(id: str, db: AsyncSession = Depends(get_db)):
    # Implementation
    pass
```


---

### PYTHON-ANNO-WC015-test_project_dependency_map.py

**Status:** CANDIDATE  
**Category:** annotations  
**Confidence:** 0.5  
**Source:** `tests/pipeline/test_project_dependency_map.py` (from GOAL-WC015)  
**Created:** 2026-07-30

Python file header convention from WC-015 (C-059).

```
# Implements: architecture/reference/components/{service}.md §{Section}
# Constitutional basis: C-NNN ({Claim Name})
```


---
