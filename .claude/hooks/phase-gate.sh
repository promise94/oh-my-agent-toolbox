#!/usr/bin/env bash

set -u
ROOT="${CLAUDE_PROJECT_DIR:-.}"
STATE_FILE="$ROOT/.claude/phase_state.json"

if [ ! -f "$STATE_FILE" ]; then
  exit 0
fi

json_get() {
  local key="$1"
  if command -v jq >/dev/null 2>&1; then
    jq -r --arg key "$key" '.[$key] // ""' "$STATE_FILE" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$STATE_FILE" "$key" <<'PY' 2>/dev/null
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        value = json.load(stream).get(sys.argv[2], "")
    print(value if value is not None else "")
except Exception:
    print("")
PY
  elif command -v python >/dev/null 2>&1; then
    python - "$STATE_FILE" "$key" <<'PY' 2>/dev/null
import json
import sys
try:
    with open(sys.argv[1]) as stream:
        value = json.load(stream).get(sys.argv[2], "")
    print(value if value is not None else "")
except Exception:
    print("")
PY
  else
    printf '%s\n' ""
  fi
}

if command -v jq >/dev/null 2>&1; then
  if ! jq empty "$STATE_FILE" >/dev/null 2>&1; then
    printf '%s\n' "[PLAN GATE] BLOCKED: .claude/phase_state.json 不是合法 JSON。"
    exit 0
  fi
elif command -v python3 >/dev/null 2>&1; then
  if ! python3 -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$STATE_FILE" >/dev/null 2>&1; then
    printf '%s\n' "[PLAN GATE] BLOCKED: .claude/phase_state.json 不是合法 JSON。"
    exit 0
  fi
elif command -v python >/dev/null 2>&1; then
  if ! python -c 'import json,sys; json.load(open(sys.argv[1]))' "$STATE_FILE" >/dev/null 2>&1; then
    printf '%s\n' "[PLAN GATE] BLOCKED: .claude/phase_state.json 不是合法 JSON。"
    exit 0
  fi
else
  printf '%s\n' "[PLAN GATE] BLOCKED: 需要 jq、python3 或 python 解析 .claude/phase_state.json。"
  exit 0
fi

stage=$(json_get workflow_stage)
review=$(json_get codex_review_status)
review_note=$(json_get codex_review_note)
phase=$(json_get current_phase)
phase_name=$(json_get phase_name)
phase_status=$(json_get phase_status)
audit=$(json_get audit_status)

if [ "$stage" = "planning" ]; then
  case "$review" in
    blocked)
      printf '%s\n' "[PLAN GATE] BLOCKED: Codex review 未完成。原因：${review_note:-unknown}"
      ;;
    needs_input)
      printf '%s\n' "[PLAN GATE] BLOCKED: Codex review 需要用户决策。原因：${review_note:-review requires user input}"
      ;;
    waived)
      printf '%s\n' "[PLAN GATE] Codex review 已 waived；请将原因写入计划并取得用户批准后再进入 execution。"
      ;;
    completed)
      printf '%s\n' "[PLAN GATE] Codex review 已完成；请处理报告、取得批准并写入 execution state。"
      ;;
    *)
      printf '%s\n' "[PLAN GATE] BLOCKED: planning 阶段尚未完成 Codex review 或 waiver。"
      ;;
  esac
  exit 0
fi

if [ "$stage" != "execution" ]; then
  exit 0
fi

case "$audit" in
  pending|needs_input|blocked|waived|completed)
    ;;
  *)
    printf '%s\n' "[PLAN GATE] BLOCKED: audit_status 无效或缺失：${audit:-missing}。当前 hook 为提示式门禁。"
    ;;
esac

if [ "$review" != "completed" ] && [ "$review" != "waived" ]; then
  printf '%s\n' "[PLAN GATE] Codex review disposition 尚未完成：${review:-missing}。当前 hook 为提示式门禁。"
fi

if [ "$phase_status" != "PASS" ]; then
  printf '%s\n' "[PHASE GATE] Phase ${phase:-?} (${phase_name:-unknown}) 尚未通过：${phase_status:-missing}。"
  exit 0
fi

if [ "$audit" = "pending" ] || [ "$audit" = "blocked" ] || [ "$audit" = "needs_input" ]; then
  printf '%s\n' "[PLAN GATE] 当前阶段已通过；最终 Codex audit 尚未完成：${audit}。"
fi

exit 0
