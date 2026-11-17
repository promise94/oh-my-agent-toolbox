# Large Plan Template

For multi-phase work: multiple modules, architecture decisions, migration, deployment.

## Template

```markdown
# [Title]

> **Execution rule:** After each Phase, run its Acceptance Criteria and check Constraints. Any deviation must be logged in the Decision Log and the plan updated before continuing. See `/planning-workflow` for full process.

## Context
Why this work exists. What problem it solves. Current state vs desired state.

## Requirements
Captured from Phase 0 clarification. Each entry: question → answer → how it constrains the plan.

| # | Question | Answer | Constraint |
|---|----------|--------|------------|
| 1 | _(filled during clarification)_ | | |

## Scope
**In**: what this plan covers.
**Out**: what is explicitly excluded and why.

## Design
Architecture decisions with rationale. Data flow. Key trade-offs.
For each major decision: what was chosen, what was rejected, why.

---

## Phase 1: [Name]

### Changes
| Op | File | What |
|----|------|------|
| Create | `path/to/new.py` | Description |
| Modify | `path/to/existing.py` | What changes |
| Delete | `path/to/old.py` | Why removed |

### Acceptance Criteria
- [ ] `pytest tests/test_x.py -v` — all pass
- [ ] `wc -l path/to/file.py` — < 400
- [ ] `grep -c "def method_" path/to/file.py` — >= 5
- [ ] `python3 -c "from module import Class"` — no error
- [ ] Regression: `pytest tests/ -v` — all existing tests pass

### Constraints
- file.py < 400 lines
- New tests >= N
- No new files > 400 lines

---

## Phase 2: [Name]
(same structure as above)

---

## Risks
| Risk | Mitigation |
|------|------------|
| X fails | Fallback to Y |

## Decision Log
| Date | What changed | Why | Affected sections |
|------|-------------|-----|-------------------|
| _(empty at plan time, filled during execution)_ |
```

## Section Rules

### Requirements
- Filled during Phase 0 clarification via the host's structured-question capability (C1).
- Each row captures: what was asked, what the user answered, how it constrains the plan.
- If user skipped clarification ("just go"), convert unresolved items to Assumptions with explicit defaults.

### Context
- One paragraph. Problem, not solution.

### Scope
- Explicit "Out" prevents scope creep. If tempting but out of scope, write it in Out with a reason.

### Design
- Every architecture decision needs "why" + "rejected alternative".
- Quantitative claims (line counts, dimensions, model names) must have matching Constraints in the relevant Phase.

### Changes
- File-level granularity. No "update the module".
- Op is Create/Modify/Delete, not "refactor" or "improve".

### Acceptance Criteria
- **Must be runnable commands** — `pytest`, `wc -l`, `grep -c`, import checks, curl calls.
- No prose like "verify it works" or "check that X is correct".
- Include a regression check in every phase.

### Constraints
- Quantitative only: line counts, test counts, file counts.
- Each constraint must be verifiable by a command in Acceptance Criteria.

### Decision Log
- Empty at plan time. Filled during execution when code diverges from plan.
- Entry format: Date | What | Why | Which plan sections affected.

### Decision Log Examples

```markdown
| 2026-04-02 | Embedding: doubao-large 1024d → doubao-vision 2048d | Original model deprecated | Phase B: B.2, B.1 |
| 2026-04-03 | orchestrator.py 1555 lines (plan: ~800) | Phase B/C added more logic than anticipated | Orch split: Constraints |
| 2026-04-03 | Flutter reputation UI deferred | Deprioritized to next sprint | Phase C: C.3, C.5 |
```
