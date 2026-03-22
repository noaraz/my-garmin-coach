---
name: plan-docs-update
description: >
  Check that an implementation plan's first task (Phase 0) covers updating all
  required MD files AND invokes the CLAUDE.md improvement skills before any code
  changes: STATUS.md, root PLAN.md, root CLAUDE.md, feature PLAN.md, feature CLAUDE.md,
  plus invocations of revise-claude-md and claude-md-improver. Use whenever reviewing
  or approving an implementation plan — especially inside the writing-plans review loop.
  Invoke when the user says "check the plan", "review the plan", "does the plan have a
  Phase 0", or asks you to enforce docs updates in a plan. If a plan is presented for
  review and has no Phase 0, flag it immediately.
---

# Plan Docs Update Enforcer

Every implementation plan must begin with a Phase 0 that updates all relevant
documentation **before** any code changes. This keeps tracking files and CLAUDE.md
files in sync, and uses the CLAUDE.md improvement skills to surface session learnings.

## What to Check

Read the plan document. Look for a Phase 0 (or first task) that explicitly covers
all **five** of these files plus **two skill invocations**:

### Required MD file updates

| File | Where | Purpose |
|------|-------|---------|
| `STATUS.md` | repo root | project-level progress tracking |
| `PLAN.md` | repo root | root feature table + status emoji |
| `CLAUDE.md` | repo root | main project instructions |
| `features/<name>/PLAN.md` | feature dir | feature-level task tracking |
| `features/<name>/CLAUDE.md` | feature dir | feature-specific patterns + gotchas |

### Required skill invocations

| Skill | When to invoke | Purpose |
|-------|---------------|---------|
| `claude-md-management:revise-claude-md` | after implementation, in Phase 0 or final task | Update CLAUDE.md files with session learnings |
| `claude-md-management:claude-md-improver` | in Phase 0 | Audit and improve all CLAUDE.md files |

## What Counts as Covered

**MD files** — a file is covered if Phase 0:
- Names it explicitly (e.g., "Update STATUS.md", "Update root PLAN.md")
- Has a checkbox step (`- [ ]`) for the update
- Includes it in the Phase 0 commit

A vague "update docs" without naming specific files does **not** count.

**Skills** — a skill is covered if Phase 0 (or the final task) has an explicit step
to invoke it, e.g.:
- `- [ ] Run claude-md-management:revise-claude-md to capture session learnings`
- `- [ ] Run claude-md-management:claude-md-improver to audit CLAUDE.md files`

## Output Format

**If everything is covered:**

```
✅ Phase 0 APPROVED — all required docs updates present:
  MD files:
  - STATUS.md ✓
  - Root PLAN.md ✓
  - Root CLAUDE.md ✓
  - features/<name>/PLAN.md ✓
  - features/<name>/CLAUDE.md ✓
  Skills:
  - revise-claude-md ✓
  - claude-md-improver ✓
```

**If anything is missing:**

```
❌ Phase 0 ISSUES FOUND — missing items:

  MD files:
  - [ ] Root PLAN.md — not mentioned in Phase 0
  - [ ] Root CLAUDE.md — not mentioned in Phase 0

  Skills:
  - [ ] revise-claude-md — no invocation step found
  - [ ] claude-md-improver — no invocation step found

Add explicit steps and checkboxes for each missing item. The plan should not be
approved until all five MD files and both skill invocations are present.
```

Only list items that are actually missing.

## Enforcement Rule

If **any** of the five MD files or either skill invocation is missing, return ISSUES
FOUND. Do not approve a plan with a partial or absent Phase 0. The fix is always the
same: add the missing item as an explicit checkbox step in Phase 0.
