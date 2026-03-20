---
name: datetime-convention
description: Enforce the project's naive UTC datetime convention. Use when writing any Python code that creates or updates datetime values for database columns. Prevents deprecated datetime.utcnow() and timezone-aware datetimes that break PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns.
---

# Datetime Convention — GarminCoach

## The Rule

All datetime values written to database columns MUST use:

```python
datetime.now(timezone.utc).replace(tzinfo=None)
```

This produces a **naive UTC datetime** compatible with PostgreSQL `TIMESTAMP WITHOUT TIME ZONE`.

## Required Import

```python
from datetime import datetime, timezone
```

## Banned Patterns

| Pattern | Why it's wrong |
|---------|----------------|
| `datetime.utcnow()` | Deprecated in Python 3.12+. Same result but inconsistent with codebase convention. |
| `datetime.now()` | Returns local time, not UTC. |
| `datetime.now(timezone.utc)` (without `.replace(tzinfo=None)`) | Timezone-aware datetime. PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` rejects it. |
| `datetime.utcnow().replace(tzinfo=timezone.utc)` | Double wrong: deprecated call + adds tzinfo back. |

## When This Applies

- Any `created_at`, `updated_at`, `start_time`, or similar column assignment
- Any `datetime.now(...)` call whose result goes into an ORM model field
- Service layer methods that mutate model timestamps before `session.commit()`

## Correct Examples

```python
# Creating a timestamp for a DB column
now = datetime.now(timezone.utc).replace(tzinfo=None)
model.updated_at = now

# Inline assignment
scheduled.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
```

## Checklist

Before committing Python code that touches datetime values:

1. Search for `datetime.utcnow()` in changed files — replace with `datetime.now(timezone.utc).replace(tzinfo=None)`
2. Search for `datetime.now()` without `timezone.utc` — add UTC
3. Verify `timezone` is in the import line: `from datetime import datetime, timezone`
4. Verify `.replace(tzinfo=None)` is present on any datetime going to a DB column
