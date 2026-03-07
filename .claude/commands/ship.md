# /ship — Feature Ship Workflow

Run this workflow when a feature is ready to ship. Follow the steps in order.

---

## 1. Code Review

Run the full test suite with coverage inside Docker:

```bash
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/ -v --cov=src --cov-report=term-missing
```

Present results to the user: total passed/failed, coverage per module, any failures.

Then invoke the `/code-review` command on the uncommitted changes:

```
/code-review uncommitted changes
```

Present any issues found (score ≥ 80) to the user.

---

## 2. Ask What to Fix

Show the findings and ask:

> "Here's the review. What would you like me to fix before opening the PR?"

Wait for the user's response. Fix any requested items, re-run the affected tests to confirm green, then continue.

---

## 3. Local Test Steps

Print this block for the user to run manually:

```bash
# Unit tests
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/unit/ -v

# Integration tests
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/integration/ -v

# Full suite + coverage
/Applications/Docker.app/Contents/Resources/bin/docker compose exec backend pytest tests/ --cov=src --cov-report=term-missing

# Smoke test the API
curl http://localhost:8000/api/health
curl http://localhost:8000/api/profile
```

---

## 4. Update All Relevant Docs

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

## 5. Commit and Open PR

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
- [ ] Coverage ≥ 90%: `pytest tests/ --cov=src --cov-report=term-missing`
- [ ] API smoke test: `curl http://localhost:8000/api/health`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Return the PR URL to the user.
