# /ship — Feature Ship Workflow

Run this workflow when a feature is ready to ship. Follow the steps in order.

---

## 1. Run Tests

Run the full test suite with coverage inside Docker:

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/ -v --cov=src --cov-report=term-missing
```

Present results to the user: total passed/failed, coverage per module, any failures.

---

## 2. Lint

Run linters before opening the PR — these mirror CI exactly:

```bash
# Backend: ruff lint (catches unused imports, style violations)
cd backend && ruff check src/ tests/

# Frontend: TypeScript type check + build
cd frontend && npm run build
```

Fix any errors before continuing. For ruff: `ruff check --fix src/ tests/` auto-fixes safe issues.

---

## 3. Security Audit

Run security checks before opening the PR:

```bash
# Frontend: fail on high-severity CVEs
cd frontend && npm audit --audit-level=high

# Backend: fail on known vulnerabilities
pip-audit --ignore-vuln GHSA-25h7-pfq9-p65f  # ecdsa, no fix available
```

If `npm audit` flags new high/critical CVEs: run `npm audit fix` (or `npm audit fix --force` if needed), commit `package-lock.json`, then continue.

---

## 4. Ask What to Fix (Pre-PR)

Show the test results and ask:

> "Tests look good. Anything to fix before I open the PR?"

Wait for the user's response. Fix any requested items, re-run the affected tests to confirm green, then continue.

---

## 5. Local Test Steps

Print this block for the user to run manually:

```bash
# Unit tests
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/unit/ -v

# Integration tests
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/integration/ -v

# Full suite + coverage
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/ --cov=src --cov-report=term-missing

# Smoke test the API
curl http://localhost:8000/api/v1/health
```

---

## 6. Update All Relevant Docs

### STATUS.md
- Mark all completed tasks as ✅
- Update "Last updated" line with today's date and feature name
- Update `## Current Focus` to the next feature

### CLAUDE.md
- Add any new patterns, gotchas, or conventions discovered
- Update the Features table if new implementation files were added

### `features/<name>/PLAN.md`
- Check off all completed tasks
- Note any deviations from the original plan

### `features/<name>/CLAUDE.md`
- Add gotchas, edge cases, or patterns specific to this feature
- Update mock/fixture patterns if they changed

---

## 7. Commit and Open PR

Stage and review:
```bash
git add -A
git status
```

Commit (conventional style):
```bash
git commit -m "feat: <short description>"
```

Open the PR:
```bash
gh pr create \
  --title "feat: <title>" \
  --body "$(cat <<'EOF'
## Summary
- <bullet 1>
- <bullet 2>
- <bullet 3>

## Test plan
- [ ] Unit tests pass: `pytest tests/unit/ -v`
- [ ] Integration tests pass: `pytest tests/integration/ -v`
- [ ] Coverage ≥ 80%: `pytest tests/ --cov=src --cov-report=term-missing`
- [ ] API smoke test: `curl http://localhost:8000/api/v1/health`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Return the PR URL to the user.

---

## 8. Code Review on the PR

Now that the PR exists, invoke the `/code-review` command on it:

```
/code-review <PR URL>
```

The review will post comments directly on the PR. Present any issues found (score ≥ 80) to the user and offer to fix them.
