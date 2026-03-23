#!/bin/bash
# Auto-ruff after Python file edit
# Reads tool input JSON from stdin (Claude Code hook format)
INPUT=$(cat 2>/dev/null || echo "{}")
FILE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('file_path', d.get('path', '')))" 2>/dev/null || echo "")

[[ "$FILE" == *.py ]] || exit 0
[[ -f "$FILE" ]] || exit 0

REPO_ROOT="$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$REPO_ROOT"

if [[ -f "backend/.venv/bin/ruff" ]]; then
  RUFF="backend/.venv/bin/ruff"
elif [[ -f ".venv/bin/ruff" ]]; then
  RUFF=".venv/bin/ruff"
else
  exit 0
fi

$RUFF check --fix "$FILE" 2>/dev/null || true
$RUFF format "$FILE" 2>/dev/null || true
