#!/bin/bash
# Block edits to .env files (except .env.example) and lock files
# Reads tool input JSON from stdin (Claude Code hook format)
INPUT=$(cat 2>/dev/null || echo "{}")
FILE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('file_path', d.get('path', '')))" 2>/dev/null || echo "")

[[ -z "$FILE" ]] && exit 0
BASENAME=$(basename "$FILE")

# Block .env files (except .env.example and .env.test)
if [[ "$BASENAME" == .env* && "$BASENAME" != *.example && "$BASENAME" != *.test ]]; then
  echo "BLOCKED: Direct edits to '$BASENAME' are not allowed." >&2
  echo "Edit via terminal or explicitly approve this action." >&2
  exit 2
fi

# Block lock files (must be updated via package manager)
if [[ "$BASENAME" == "package-lock.json" || "$BASENAME" == "uv.lock" ]]; then
  echo "BLOCKED: '$BASENAME' must be updated via 'npm install' or 'pip', not direct edit." >&2
  exit 2
fi

exit 0
