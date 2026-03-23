---
name: coverage-gate
description: Run backend and frontend test coverage and fail if below threshold. Integrated into /ship step 1. Claude invokes this automatically during ship workflow.
user-invocable: false
---

Run after tests pass. Check coverage against minimum thresholds.

## Backend coverage
```bash
docker compose exec backend pytest --cov=src --cov-report=term-missing -q
```

Parse terminal output for coverage percentages:
- **Total coverage** must be ≥ **80%**
- **`src/zone_engine/`** must be ≥ **95%**
- **`src/workout_resolver/`** must be ≥ **95%**

## Frontend coverage
```bash
cd frontend && npm run test:coverage
```

Parse output:
- **Total coverage** must be ≥ **80%**

## Output

If any threshold is missed:
```
Coverage gate FAILED:
  backend total: 74% (need 80%)
  src/zone_engine: 91% (need 95%)
Do not open PR until resolved.
```

If all pass:
```
Coverage gate PASSED — all thresholds met.
  backend: 87% | zone_engine: 97% | workout_resolver: 96%
  frontend: 82%
```
