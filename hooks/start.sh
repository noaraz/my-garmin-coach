#!/bin/bash
# Hook: session start
# Summarizes project status and asks whether to continue

echo "=========================================="
echo "  GarminCoach — Session Start"
echo "=========================================="
echo ""

# Auto-create a feature branch if on main
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$CURRENT_BRANCH" = "main" ]; then
    FOCUS=$(grep "^## Current Focus:" STATUS.md 2>/dev/null | sed 's/## Current Focus: //' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | tr -s '-' | sed 's/^-//;s/-$//')
    if [ -z "$FOCUS" ]; then
        FOCUS="work-$(date +%Y-%m-%d)"
    fi
    BRANCH="feature/$FOCUS"
    git checkout -b "$BRANCH" 2>/dev/null
    echo "🌿 Created branch: $BRANCH"
    echo ""
fi

if [ ! -f STATUS.md ]; then
    echo "⚠️  STATUS.md not found. Create it before starting work."
    exit 0
fi

# Current focus
echo "📍 $(grep "^## Current Focus:" STATUS.md || echo "No current focus set")"
echo ""

# Count done / in progress / total
DONE=$(grep -c "✅" STATUS.md 2>/dev/null || echo 0)
IN_PROGRESS=$(grep -c "🟡" STATUS.md 2>/dev/null || echo 0)
NOT_STARTED=$(grep -c "⬜" STATUS.md 2>/dev/null || echo 0)
BLOCKED=$(grep -c "❌" STATUS.md 2>/dev/null || echo 0)
TOTAL=$((DONE + IN_PROGRESS + NOT_STARTED + BLOCKED))

echo "📊 Progress: $DONE/$TOTAL done, $IN_PROGRESS in progress, $NOT_STARTED remaining"
if [ "$BLOCKED" -gt 0 ]; then
    echo "   ❌ $BLOCKED blocked"
fi
echo ""

# Show in-progress tasks
IP_LINES=$(grep "🟡" STATUS.md)
if [ -n "$IP_LINES" ]; then
    echo "🟡 In Progress:"
    echo "$IP_LINES" | sed 's/^/   /'
    echo ""
fi

# Show next not-started tasks (first 5)
echo "⬜ Next up:"
grep "⬜" STATUS.md | head -5 | sed 's/^/   /'
echo ""

# Show any notes
NOTES=$(sed -n '/^## Notes/,/^$/p' STATUS.md | grep -v "^## Notes" | grep -v "^<!--" | grep -v "^-->" | grep -v "^$")
if [ -n "$NOTES" ]; then
    echo "📝 Notes:"
    echo "$NOTES" | sed 's/^/   /'
    echo ""
fi

# Run tests to check current state
echo "=========================================="
echo "  Test Status"
echo "=========================================="

if [ -f backend/pyproject.toml ]; then
    cd backend 2>/dev/null
    if command -v pytest &> /dev/null; then
        RESULT=$(pytest tests/ --tb=no -q 2>&1 | tail -3)
        echo "  Backend: $RESULT"
    elif [ -f ../docker-compose.yml ]; then
        RESULT=$(docker compose exec -T backend pytest tests/ --tb=no -q 2>&1 | tail -3)
        echo "  Backend: $RESULT"
    else
        echo "  Backend: ⚠️ cannot run (no pytest or docker)"
    fi
    cd .. 2>/dev/null
else
    echo "  Backend: not scaffolded yet"
fi

if [ -f frontend/package.json ] && [ -d frontend/node_modules ]; then
    cd frontend 2>/dev/null
    RESULT=$(npx vitest run --reporter=verbose 2>&1 | tail -3)
    echo "  Frontend: $RESULT"
    cd .. 2>/dev/null
elif [ -f frontend/package.json ]; then
    echo "  Frontend: node_modules not installed"
else
    echo "  Frontend: not scaffolded yet"
fi

echo ""
echo "=========================================="
echo ""
echo "  Summary complete. Read the relevant"
echo "  feature PLAN.md in docs/features/ for"
echo "  detailed tasks and test tables."
echo ""
echo "  Should I continue with the next task?"
echo "=========================================="
