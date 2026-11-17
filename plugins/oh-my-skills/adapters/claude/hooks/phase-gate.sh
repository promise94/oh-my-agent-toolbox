#!/usr/bin/env bash

set -u
ROOT="${PLAN_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-.}}"
STATE_DIR="${PLAN_STATE_DIR:-.claude}"
STATE_FILE="$ROOT/$STATE_DIR/phase_state.json"

if [ ! -f "$STATE_FILE" ]; then
  exit 0
fi

python_bin="$(command -v python3 || command -v python || true)"
if [ -z "$python_bin" ]; then
    printf '%s\n' "[PLAN GATE] BLOCKED: 需要 jq、python3 或 python 解析状态文件。"
  exit 0
fi
"$python_bin" - "$STATE_FILE" <<'PY'
import json
import sys

try:
    state = json.loads(open(sys.argv[1], encoding="utf-8").read())
except Exception:
    print("[PLAN GATE] BLOCKED: 状态文件不是合法 JSON。")
    raise SystemExit(0)

stage = state.get("workflow_stage")
review = state.get("review_status", state.get("codex_review_status", ""))
review_note = state.get("review_note", state.get("codex_review_note", ""))
audit = state.get("audit_status", "")
phase = state.get("current_phase", "?")
name = state.get("phase_name", "unknown")
status = state.get("phase_status", "missing")
if stage == "planning":
    if review == "pending" or not review:
        print("[PLAN GATE] BLOCKED: planning 阶段尚未完成独立 review。")
    elif review == "blocked":
        print(f"[PLAN GATE] BLOCKED: 独立 review 未完成。原因：{review_note or 'unknown'}")
    elif review == "needs_input":
        print(f"[PLAN GATE] BLOCKED: 独立 review 需要用户决策。原因：{review_note or 'review requires user input'}")
    else:
        print(f"[PLAN GATE] planning review status: {review}")
    raise SystemExit(0)
if stage != "execution":
    raise SystemExit(0)
if review not in {"completed", "waived"}:
    print(f"[PLAN GATE] 独立 review disposition 尚未完成：{review or 'missing'}。")
if status != "PASS":
    print(f"[PHASE GATE] Phase {phase} ({name}) 尚未通过：{status}。")
elif audit in {"pending", "blocked", "needs_input"}:
    print(f"[PLAN GATE] 当前阶段已通过；最终 audit 尚未完成：{audit}。")
elif not audit:
    print("[PLAN GATE] BLOCKED: audit_status 无效或缺失：missing。当前 hook 为提示式门禁。")
PY
