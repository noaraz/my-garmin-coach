---
name: plan-phase0-enforcer
description: >
  Check that an implementation plan's first task (Phase 0 / Task 1) covers updating
  all required MD files before any code changes: STATUS.md, root CLAUDE.md, and the
  feature's PLAN.md and CLAUDE.md. Use this whenever reviewing or approving an
  implementation plan — especially inside the writing-plans review loop. Invoke when
  the user says "check the plan", "review the plan", "does the plan have a Phase 0",
  or asks you to enforce MD file updates in a plan. If a plan is presented for review
  and has no Phase 0, flag it immediately.
---

# Plan Phase 0 Enforcer

Every implementation plan must begin with a task that updates all relevant MD
documentation **before** any code changes. This keeps STATUS.md, CLAUDE.md files,
and feature PLAN.md in sync with the work, which is the project's standard workflow.

## What to Check

Read the plan document. Look for a Phase 0, Task 0, or first task that explicitly
covers updating **all four** of these files:

| File | Where | Purpose |
|------|-------|---------|
| `STATUS.md` | repo root | project-level progress tracking |
| `CLAUDE.md` | repo root | main project instructions |
| `features/<name>/PLAN.md` | feature dir | feature-level task tracking |
| `features/<name>/CLAUDE.md` | feature dir | feature-specific patterns + gotchas |

## What Counts as Covered

A file is covered if Phase 0 (or the first task):
- Names it explicitly (e.g., "Update STATUS.md", "Update features/plan-coach/PLAN.md")
- Has a checkbox step (`- [ ]`) for the update
- Includes it in the Phase 0 commit

A vague "update docs" step without naming specific files does **not** count — it's too
easy to skip one file when nothing specific is called out.

## Output Format

**If all four files are covered:**

```
✅ Phase 0 APPROVED — all required MD updates present:
  - STATUS.md ✓
  - Root CLAUDE.md ✓
  - features/<name>/PLAN.md ✓
  - features/<name>/CLAUDE.md ✓
```

**If any are missing:**

```
❌ Phase 0 ISSUES FOUND — missing MD file updates:
  - [ ] STATUS.md — not mentioned in Phase 0
  - [ ] Root CLAUDE.md — not mentioned in Phase 0
  - [ ] features/<name>/PLAN.md — not mentioned in Phase 0
  - [ ] features/<name>/CLAUDE.md — not mentioned in Phase 0

Add a Phase 0 task at the top of the plan with an explicit step and commit for each
missing file. The plan should not be approved until these are present.
```

Only list the files that are actually missing. If 3 of 4 are present, only flag the one
that's missing.

## Enforcement Rule

If **any** of the four files is missing from Phase 0, return ISSUES FOUND. Do not
approve a plan with a partial or absent Phase 0. The fix is always the same: add the
missing file as an explicit step in Phase 0 with its own checkbox.
