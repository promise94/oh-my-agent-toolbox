# Small Plan Template

For single-phase work: < 10 files, no architecture decisions, no migration.

## Template

```markdown
# [Title]

> **Execution rule:** After completing all changes, run every Verify item. Any deviation from this plan must be documented before proceeding. See `/planning-workflow` for full process.

## Context
Why this work exists. What problem it solves. One paragraph.

## Assumptions
Confirmed via clarification. If user skipped Q&A, list defaults here.
- Confirmed: ...
- Assumed (not confirmed): ...

## Changes
| Op | File | What |
|----|------|------|
| Create | `path/to/new.py` | Description |
| Modify | `path/to/existing.py` | What changes |
| Delete | `path/to/old.py` | Why removed |

## Verify
- [ ] `command` — expected output
- [ ] `command` — expected output
- [ ] Regression: `test command` — all pass
```

## Rules

- **Assumptions** must distinguish "Confirmed" (user answered) vs "Assumed" (defaulted, not confirmed)
- **Changes** must be file-level, not "update the module"
- **Verify** must be runnable commands, not "check that it works"
- Include a regression check (existing tests still pass)
- If you find yourself adding a second phase, switch to [large-plan.md](./large-plan.md)

## Example

```markdown
# GitLab Code Review Skill

## Context
Need `/code-review` for the configured self-hosted GitLab instance,
adapted from the official GitHub code-review plugin.

## Changes
| Op | File | What |
|----|------|------|
| Create | `<host-skills-dir>/code-review/SKILL.md` | Skill file, gh→glab commands, PR→MR terminology |

## Verify
- [ ] `/code-review` invocable in Claude Code session
- [ ] `glab auth status` — authenticated to the configured GitLab host
- [ ] Skill uses `glab mr view/diff/note` not `gh pr`
```

## After Completion

Run every Verify item. All pass? Done. Any deviation? Note what changed and why.
