#!/usr/bin/env bash

set -u
# The delegated adapter resolves PLAN_PROJECT_DIR/CLAUDE_PROJECT_DIR and owns all gate logic.
SCRIPT_DIR="${BASH_SOURCE[0]%/*}"
if [ "$SCRIPT_DIR" = "${BASH_SOURCE[0]}" ]; then SCRIPT_DIR="."; fi
exec /bin/bash "$SCRIPT_DIR/../adapters/claude/hooks/phase-gate.sh" "$@"
