#!/bin/bash
# Hook: session end
# Runs tests and reminds to update STATUS.md

echo "=========================================="
echo "  GarminCoach — Session End"
echo "=========================================="
echo ""

# Run full test suite
echo "🧪 Running full test suite before ending..."
echo ""

TESTS_PASSED=true

if [ -f backend/pyproject.toml ]; then
    cd backend
    if command -v pytest &> /dev/null; then
        pytest tests/ -v --tb=short
        if [ $? -ne 0 ]; then
            TESTS_PASSED=false
        fi
    elif [ -f ../docker-compose.yml ]; then
        docker compose exec -T backend pytest tests/ -v --tb=short
        if [ $? -ne 0 ]; then
            TESTS_PASSED=false
        fi
    fi
    cd ..
fi

if [ -f frontend/package.json ] && [ -d frontend/node_modules ]; then
    cd frontend
    npx vitest run --reporter=verbose
    if [ $? -ne 0 ]; then
        TESTS_PASSED=false
    fi
    cd ..
fi

echo ""
echo "=========================================="

if [ "$TESTS_PASSED" = true ]; then
    echo "  ✅ All tests passing"
else
    echo "  ❌ SOME TESTS FAILING — fix before ending session"
fi

echo ""
echo "  📋 Remember to update STATUS.md:"
echo "     - Mark completed tasks with ✅"
echo "     - Mark in-progress tasks with 🟡"
echo "     - Update 'Current Phase' if phase changed"
echo "     - Update 'Last updated' date"
echo "     - Add any notes about decisions or blockers"
echo "=========================================="
