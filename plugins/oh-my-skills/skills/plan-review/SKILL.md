---
name: plan-review
description: |
  Cross-model plan QA — send plan to Codex for independent review.
  Use when: plan is written and self-reviewed, before user approval.
  Requires: codex@openai-codex plugin installed.
argument-hint: [plan-file-path]
allowed-tools: Bash, Read, Write, Glob, Grep, AskUserQuestion, Skill
---

# Codex Plan Review

Codex independently reviews a plan against the actual codebase via the official Codex plugin.

## Step 0: Confirm Review Path

If `/codex:rescue` is in the available skills list, proactively use `AskUserQuestion` to ask whether the user wants review/waiver for this plan.

- If the user chooses review, continue.
- If the user chooses waiver, write waived planning state instead:

```bash
PYTHON_BIN="$(command -v python3 || command -v python)"
"$PYTHON_BIN" - <<'PY' "$CLAUDE_PROJECT_DIR/.claude/phase_state.json"
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else {}
data["workflow_stage"] = "planning"
data["codex_review_status"] = "waived"
data["codex_review_note"] = "user approved skip for this plan"
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY
```

Then tell the user that the plan may continue only after the waiver reason is recorded in the plan's disposition or decision log.

If `/codex:rescue` is NOT in the available skills list, use `AskUserQuestion` to ask whether the user wants to waive Codex review for **this plan only**.


- If the user does **not** explicitly approve a waiver, write blocked planning state first, then tell the user:

```bash
PYTHON_BIN="$(command -v python3 || command -v python)"
"$PYTHON_BIN" - <<'PY' "$CLAUDE_PROJECT_DIR/.claude/phase_state.json"
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else {}
data["workflow_stage"] = "planning"
data["codex_review_status"] = "blocked"
data["codex_review_note"] = "plugin missing"
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY
```

> plan-review requires the official Codex plugin. Install it:
> ```
> /plugin marketplace add openai/codex-plugin-cc
> /plugin install codex@openai-codex
> /reload-plugins
> ```

Then **stop**.

- If the user explicitly approves a waiver for this plan, write waived planning state instead:

```bash
PYTHON_BIN="$(command -v python3 || command -v python)"
"$PYTHON_BIN" - <<'PY' "$CLAUDE_PROJECT_DIR/.claude/phase_state.json"
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else {}
data["workflow_stage"] = "planning"
data["codex_review_status"] = "waived"
data["codex_review_note"] = "user approved skip because Codex is unavailable"
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY
```

Then tell the user that the plan may continue only after the waiver reason is recorded in the plan's disposition or decision log.

## Step 0.5: Quick Codex Setup Preflight

Before building context or delegating the review, invoke `/codex:setup` once.

- If setup reports Codex is ready, continue.
- If setup reports Codex is unavailable, not authenticated, or blocked by a permission/environment issue, write blocked planning state using the existing Step 3 blocked-state command with a concise note such as `codex setup failed`, then stop.
- Do not run an extra smoke task here; keep this preflight lightweight.

## Step 1: Locate Plan and Build Context

If an argument is provided, verify it exists and use it as `{PLAN_PATH}`. Otherwise read `$CLAUDE_PROJECT_DIR/.claude/phase_state.json` and use `plan_path` as `{PLAN_PATH}`.

If `plan_path` is missing, stop and ask the user to specify the plan file or initialize planning state with `/planning-workflow` first. Do not fall back to the most recent plan file. Do not create a new plan file when updating an existing plan.

Extract filename without extension as `{PLAN_ID}`.

Read the plan file. Note phase count and names.

Then write a requirement summary (5-8 sentences) from the current conversation to `$CLAUDE_PROJECT_DIR/.claude/temp/codex-plan-context-{PLAN_ID}.md`, covering: goal, constraints, Phase 0 decisions, assumptions.

## Step 2: Delegate to Codex

Use `/codex:rescue` to delegate the review. Pass this prompt:

> Review the plan at `{PLAN_PATH}` against the actual codebase.
> Also read `$CLAUDE_PROJECT_DIR/.claude/temp/codex-plan-context-{PLAN_ID}.md` for requirement context and `CLAUDE.md` for project context.
>
> Checklist:
> 1. Is the plan self-contained?
> 2. Does each Phase map to a clear requirement?
> 3. Are Acceptance Criteria runnable commands (not prose)?
> 4. Are Constraints quantitative?
> 5. Missing phases? (migration, rollback, error handling, edge cases)
> 6. Does the plan account for existing code? (read actual files it plans to modify)
> 7. Phase dependencies correct?
>
> For each finding output:
> ### Codex Finding #N — <title>
> - **Severity**: Critical / Important / Suggestion
> - **Affects Phase**: <number>
> - **Issue**: <description>
> - **Recommendation**: <specific fix>
>
> Also output a section named `## Clarifications Needed` listing any scope changes, constraint changes, assumption gaps, dependency ambiguities, or trade-offs that require AskUserQuestion before the plan can be approved.
>
> End with: Total: X findings (Y critical, Z important, W suggestions)

## Step 3: Present and Merge

If `/codex:rescue` fails because of permissions or companion runtime issues, write blocked planning state before returning control:

```bash
PYTHON_BIN="$(command -v python3 || command -v python)"
"$PYTHON_BIN" - <<'PY' "$CLAUDE_PROJECT_DIR/.claude/phase_state.json" "<plugin missing|permission denied|companion runtime failed>"
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else {}
data["workflow_stage"] = "planning"
data["codex_review_status"] = "blocked"
data["codex_review_note"] = sys.argv[2]
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
PY
```

If the review succeeds, you must explicitly present the Codex review report back in the current conversation before asking for any merge or disposition decision.

If the report or `## Clarifications Needed` section shows critical findings, scope changes, constraint changes, assumption gaps, dependency ambiguities, or other trade-offs that require a user decision:

1. Write planning state with `codex_review_status=needs_input` and a short `codex_review_note`.
2. Use `AskUserQuestion` to discuss those decisions with the user.
3. Update the same `{PLAN_PATH}` with the clarified decisions or disposition.
4. Only after the report has been presented and the required discussion is complete, write planning state with `codex_review_status=completed`.

If the review succeeds without needing more input, present the findings with severity breakdown, ask whether to merge them into the same `{PLAN_PATH}`, and then write planning state with `codex_review_status=completed`.

If approved, append to the same plan file (do NOT create a new plan file and do NOT modify existing content):

```markdown
## Codex QA Review

_Reviewed through Codex on <date>_

<findings>
```

Then record the disposition in the same plan before continuing:
- merged into the plan; or
- not merged, with an explicit note explaining why the findings were not adopted

After merging, clean up the temporary context file:
```bash
rm -f "$CLAUDE_PROJECT_DIR/.claude/temp/codex-plan-context-{PLAN_ID}.md"
```\n
