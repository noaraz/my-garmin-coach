---
name: new-feature
description: Scaffold a new GarminCoach feature with all required directories, PLAN.md, CLAUDE.md, and doc updates (STATUS.md, root PLAN.md, root CLAUDE.md). Invoke when starting any new feature.
disable-model-invocation: true
---

Usage: `/new-feature <feature-name> "<short description>"`

## Steps

### 1. Create feature directory
```
features/<feature-name>/
```

### 2. Create `features/<feature-name>/PLAN.md`
```markdown
# <Feature Name>

## Goal
<description>

## Data Model
<!-- SQLModel tables, new fields, migrations needed -->

## API Routes
<!-- Endpoint, method, request schema, response schema -->

## Tests
| Test | Type | File |
|------|------|------|
|      |      |      |

## Frontend Components
<!-- Pages, components, context changes, hooks -->

## Phases
- [ ] Phase 1: ...
- [ ] Phase 2: ...
```

### 3. Create `features/<feature-name>/CLAUDE.md`
```markdown
# <Feature Name> — Patterns & Gotchas

<!-- Fill in during implementation with: patterns discovered, gotchas hit, decisions made -->
```

### 4. Update root `PLAN.md` Features table
Add row: `| <Feature Name> | \`features/<name>/\` | <description> | ⬜ |`

### 5. Update `STATUS.md` — add to "In Progress" section
```markdown
### <Feature Name>
- [ ] Phase 1: ...
```

### 6. Update root `CLAUDE.md` Features table
Add row matching existing format:
`| <Feature Name> | \`features/<name>/\` | <description> |`
