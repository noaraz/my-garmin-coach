#!/bin/bash
# Run matching test after editing a source file
# Reads tool input JSON from stdin (Claude Code hook format)
INPUT=$(cat 2>/dev/null || echo "{}")
FILE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('file_path', d.get('path', '')))" 2>/dev/null || echo "")

[[ -f "$FILE" ]] || exit 0
REPO_ROOT="$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null)" || exit 0

# Backend: src file → matching unit test
if [[ "$FILE" == */backend/src/* && "$FILE" == *.py ]]; then
  MODULE=$(basename "$FILE" .py)
  TEST="$REPO_ROOT/backend/tests/unit/test_${MODULE}.py"
  if [[ -f "$TEST" ]]; then
    echo "--- auto-test: test_${MODULE}.py ---"
    VENV="$REPO_ROOT/backend/.venv/bin/pytest"
    if [[ -x "$VENV" ]]; then
      "$VENV" "$TEST" -q 2>&1 | tail -8 || true
    else
      PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" \
        docker compose -f "$REPO_ROOT/docker-compose.yml" exec -T backend \
        pytest "tests/unit/test_${MODULE}.py" -q 2>&1 | tail -8 || true
    fi
  fi

# Frontend: src file → matching .test file
elif [[ "$FILE" == */frontend/src/* && "$FILE" != *.test.* && "$FILE" != */tests/* ]]; then
  BASE="${FILE%.tsx}"
  BASE="${BASE%.ts}"
  for EXT in .test.tsx .test.ts; do
    TEST="${BASE}${EXT}"
    if [[ -f "$TEST" ]]; then
      echo "--- auto-test: $(basename "$TEST") ---"
      cd "$REPO_ROOT/frontend"
      npx vitest run "$(basename "$TEST")" --reporter=verbose 2>&1 | tail -10 || true
      break
    fi
  done
fi
