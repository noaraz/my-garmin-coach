#!/bin/bash
# TypeScript type-check after TS/TSX edit
# Reads tool input JSON from stdin (Claude Code hook format)
INPUT=$(cat 2>/dev/null || echo "{}")
FILE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('file_path', d.get('path', '')))" 2>/dev/null || echo "")

[[ "$FILE" == *.ts || "$FILE" == *.tsx ]] || exit 0
[[ "$FILE" == *.test.ts || "$FILE" == *.test.tsx ]] && exit 0  # skip test files
[[ -f "$FILE" ]] || exit 0

REPO_ROOT="$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null)" || exit 0
FRONTEND="$REPO_ROOT/frontend"
[[ -f "$FRONTEND/tsconfig.json" ]] || exit 0

cd "$FRONTEND"
echo "--- tsc check ($(basename "$FILE")) ---"
npx tsc --noEmit 2>&1 | grep -E "error TS" | head -10 || true
