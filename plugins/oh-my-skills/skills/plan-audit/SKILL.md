---
name: plan-audit
description: |
  Cross-model final audit — Codex verifies implementation matches the plan.
  Use when: all phases implemented, before declaring done.
  Requires: codex@openai-codex plugin installed.
argument-hint: [plan-file-path]
allowed-tools: Bash, Read, Write, Glob, Grep, AskUserQuestion, Skill
---

# Codex Plan Audit

Codex independently audits whether implementation matches the plan via the official Codex plugin.

## Step 0: Confirm Audit Path

If `/codex:rescue` is in the available skills list, proactively use `AskUserQuestion` to ask whether the user wants audit/waiver for this plan.

- If the user chooses audit, continue.
- If the user chooses waiver, tell the user that the final audit was skipped by user choice for this plan and stop.

If `/codex:rescue` is NOT in the available skills list, tell the user:

> plan-audit requires the official Codex plugin. Install it:
> ```
> /plugin marketplace add openai/codex-plugin-cc
> /plugin install codex@openai-codex
> /reload-plugins
> ```

Then **stop**.

## Step 0.5: Quick Codex Setup Preflight

Before building the implementation summary or delegating the audit, invoke `/codex:setup` once.

- If setup reports Codex is ready, continue.
- If setup reports Codex is unavailable, not authenticated, or blocked by a permission/environment issue, tell the user the audit is blocked by `codex setup failed`, include the setup output, and stop.
- Do not run an extra smoke task here; keep this preflight lightweight.

## Step 1: Locate Plan and Build Implementation Summary

If an argument is provided, verify it exists and use it as `{PLAN_PATH}`. Otherwise read `$CLAUDE_PROJECT_DIR/.claude/phase_state.json` and use `plan_path` as `{PLAN_PATH}`.

If `plan_path` is missing, stop and ask the user to specify the plan file. Do not fall back to the most recent plan file. Do not create a new plan file when auditing an existing plan.

Extract filename without extension as `{PLAN_ID}`.

**Read the plan file first.** Then build a plan-aware implementation summary at `$CLAUDE_PROJECT_DIR/.claude/temp/codex-plan-impl-{PLAN_ID}.md`:

For each Phase in the plan:
1. List files the Phase planned to change
2. Check if modified: `git log --oneline -5 -- <file>`
3. Check if planned tests exist: `test -f <test_file>`
4. Note any Decision Log deviations

Also include git diff stats:
```bash
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo main)
git diff "$DEFAULT_BRANCH"...HEAD --stat 2>/dev/null || git diff HEAD~10..HEAD --stat
```

Format as:
```markdown
# Implementation Summary for {PLAN_ID}

## Phase A: <name>
- Planned files: <list>
- Modified: yes/no per file
- Tests: exist/missing

## Full Diff Stats
<output>
```

## Step 2: Delegate to Codex

Use `/codex:rescue` to delegate the audit. Pass this prompt:

> Audit the implementation against the plan at `{PLAN_PATH}`.
> Also read `$CLAUDE_PROJECT_DIR/.claude/temp/codex-plan-impl-{PLAN_ID}.md` for implementation summary and `CLAUDE.md` for project context.
>
> For EACH phase check:
> 1. Were all listed file changes made?
> 2. Do Acceptance Criteria pass? (check test files exist)
> 3. Are Constraints met? (actual vs expected values)
> 4. Decision Log deviations justified?
>
> Also check:
> 5. Unplanned changes?
> 6. Skipped or partial phases?
> 7. Leftover TODOs or placeholder code?
>
> Output per phase:
> ### Phase N: <name> — <PASS|FAIL|PARTIAL>
> - AC: <pass/fail> — <evidence>
> - Constraint: <met/violated> — <actual vs expected>
>
> End with Summary: phases passed, AC passed, constraints met, verdict (APPROVED/NEEDS REVISION), key gaps.

## Step 3: Present and Append

Present per-phase status, verdict, gaps. Ask: "Append audit to the same plan? (y/n)"

If approved, append to the same plan file (do NOT create a new plan file and do NOT modify existing content):

```markdown
## Codex Final Audit

_Audited through Codex on <date>_

<audit report>
```

After appending, clean up the temporary implementation summary:
```bash
rm -f "$CLAUDE_PROJECT_DIR/.claude/temp/codex-plan-impl-{PLAN_ID}.md"
```
