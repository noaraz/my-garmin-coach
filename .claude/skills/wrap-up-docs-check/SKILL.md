---
name: wrap-up-docs-check
description: >
  Final quality gate for GarminCoach feature work. Invoke this skill whenever
  the user signals they are done — phrases like "all good", "looks good",
  "ship it", "done", "approved", "merge it", "that's it", "we're done",
  "close the PR", or any similar sign-off. Also invoke proactively after
  completing a full implementation plan before opening a PR.

  The skill validates that root STATUS.md, PLAN.md, and CLAUDE.md are updated
  for the current feature, checks that the relevant feature subfolder under
  features/ has its own PLAN.md and CLAUDE.md updated, and runs
  claude-md-management:revise-claude-md on every CLAUDE.md touched by this
  branch. Missing updates are fixed automatically — this is an action skill,
  not a report skill.
---

# Wrap-Up Docs Check

You are the final quality gate before a feature is considered complete. Your job is to make sure all documentation is consistent and up to date. Do not just report — fix what is missing.

## Step 1: Understand What Changed

Run these commands to get the full picture of the current branch:

```bash
git diff main..HEAD --name-only
git log main..HEAD --oneline
```

From the changed files, infer:
- **Which feature** this branch implements (look for paths like `features/plan-coach/`, `frontend/src/components/plan-coach/`, `backend/src/api/routers/calendar.py`, etc.)
- **Which root docs** were touched (STATUS.md, PLAN.md, CLAUDE.md)
- **Which feature docs** were touched (features/<name>/PLAN.md, features/<name>/CLAUDE.md)
- **Which CLAUDE.md files** were touched (root + any feature-level)

## Step 2: Check the Four Required Files

Every feature branch must touch all four of these before it is done:

| File | What to check |
|------|--------------|
| `STATUS.md` | Current feature has a section; all tasks show ✅; "Last updated" line reflects today's work |
| `PLAN.md` (root) | Feature row exists in the Features table; marked ✅ if complete |
| `CLAUDE.md` (root) | Any new patterns, gotchas, or conventions from this feature are documented |
| `features/<name>/PLAN.md` | All completed tasks checked off; no stale ⬜ for work that's done |
| `features/<name>/CLAUDE.md` | Patterns, edge cases, and implementation decisions from this feature are captured |

For each file that is missing from the diff or has stale content, fix it now. Don't ask — update it.

### How to update each file

**STATUS.md**: Find the feature section. Mark all completed tasks ✅. Update the "Last updated" line at the top to today's date and feature name.

**root PLAN.md**: Find the feature row in the Features or Plan Coach table. Update the emoji to ✅ if complete.

**root CLAUDE.md**: Add any new patterns discovered during implementation. Focus on things that will save future Claude sessions time: gotchas, non-obvious decisions, API quirks, test setup oddities. Don't add things already visible in the code.

**features/<name>/PLAN.md**: Check off all completed tasks. If new tasks were added during implementation, add them and mark ✅.

**features/<name>/CLAUDE.md**: Document patterns specific to this feature — how services interact, what mock patterns are used in tests, any edge cases discovered.

## Step 3: Run revise-claude-md on All Touched CLAUDE.md Files

After updating docs manually, invoke the `claude-md-management:revise-claude-md` skill. This audits every CLAUDE.md in the repository and improves quality, removes stale content, and adds missing patterns from recent code.

```
Skill: claude-md-management:revise-claude-md
```

Let it run to completion before declaring the wrap-up done.

## Step 4: Report

After completing all updates, give the user a concise summary:

```
✅ Wrap-up complete

Updated:
- STATUS.md — Phase 6 tasks marked ✅, Last updated line refreshed
- root CLAUDE.md — Added X new patterns
- features/plan-coach/PLAN.md — All tasks checked off
- features/plan-coach/CLAUDE.md — Added Y new patterns

revise-claude-md: ran on 2 CLAUDE.md files, improved Z entries

All docs are consistent. Branch is ready to ship.
```

If nothing needed fixing, say so briefly. Don't invent problems.

## What "updated" means

A file counts as updated if it was meaningfully changed — not just if it appears in the diff. If a file was touched only because of a merge conflict resolution with no substantive content change, check manually whether the content reflects the current feature state.

## Edge cases

- **Multiple features in one branch**: Check docs for each feature directory mentioned in the diff.
- **Hotfix branches**: If this is a small bugfix (no feature subfolder), only STATUS.md and root CLAUDE.md are required. Skip the features/ check.
- **Worktree**: If running in a worktree (path contains `.claude/worktrees/`), the root of the main repo is at the worktree path — git diff still works correctly from there.
