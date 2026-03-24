# Claude Code Automation — GarminCoach

Everything added to make Claude Code smarter and faster in this repo.

---

## Quick Reference

| When you want to… | Use… |
|---|---|
| Check a PR's CI status | GitHub MCP (`mcp__github__get_pull_request_status`) |
| Query the production DB | Postgres MCP (`mcp__postgres__query`) |
| Look up library docs | context7 MCP — ask Claude: *"use context7 to look up X"* |
| Run browser automation | Playwright MCP — ask Claude to navigate/click/screenshot |
| Run a security review | `security-auditor` agent |
| Validate migrations | `migration-validator` agent |
| Check schema drift | `schema-sync` agent |
| Audit dependencies | `dependency-auditor` agent |
| Write E2E tests | `e2e-test-writer` agent |
| Run the ship workflow | `/ship` |
| Create a migration | `/alembic-migration` |
| Check API contract drift | `/api-contract-check` |
| Check coverage | `/coverage-gate` |
| Audit env vars | `/env-var-audit` |
| Scaffold a new feature | `/new-feature` |

---

## MCP Servers

MCP servers extend Claude with live tools. Configured in `.mcp.json` (env-var template) and `.mcp.json.local` (your local override with real credentials — gitignored).

### github
Replaces `gh` CLI calls. Claude uses `mcp__github__*` tools instead of `Bash(gh ...)`.

**How to verify Claude is using MCP and not `gh` CLI:**
In Claude's tool call stream, you'll see:
- **MCP (correct):** tool name `mcp__github__list_pull_requests`, `mcp__github__get_pull_request_status`, etc.
- **CLI (fallback):** `Bash` tool with command starting `gh pr ...`

If you see `Bash(gh ...)`, the GitHub MCP isn't loaded — check that `.mcp.json.local` exists with a valid token and restart Claude Code.

**Common uses:**
```
"what's the status of PR 54?"           → mcp__github__get_pull_request_status
"list open PRs"                          → mcp__github__list_pull_requests
"show me the files changed in PR 54"    → mcp__github__get_pull_request_files
"add a comment to issue 12"             → mcp__github__add_issue_comment
"create a PR"                            → mcp__github__create_pull_request
```

### postgres
Direct read-only queries against the Neon production database.

**Common uses:**
```
"how many users are in the DB?"
"show me all training plans created this week"
"query the garmin_activity table for user 1"
```
Uses `mcp__postgres__query` — SELECT only, read-only role.

### context7
Live documentation lookup for any library. Prevents Claude from hallucinating outdated API signatures.

**Common uses:**
```
"use context7 to look up SQLAlchemy async session patterns"
"use context7 for React Testing Library findByRole docs"
"use context7 for FastAPI dependency injection examples"
```

### playwright
Browser automation from inside Claude — navigate, click, fill forms, take screenshots.

**Common uses:**
```
"navigate to localhost:5173 and take a screenshot"
"click the Login button and fill in the email field"
"check if the calendar page loads without errors"
```

### memory
Persistent knowledge graph across Claude sessions. Claude can store and retrieve entities/relations.

**Common uses:**
```
"remember that the Garmin sync endpoint is at /api/v1/sync/all"
"what do you know about the zone engine?"
```

---

## Hooks

Hooks run automatically — no invocation needed. They fire when Claude edits files.

### pre_edit_guard
**Triggers:** before any file edit
**Blocks:** edits to `.env`, `.env.*`, `package-lock.json`, `poetry.lock`, `pyproject.toml` (lock sections)
**Why:** prevents accidental credential exposure and lock file corruption

### post_python_edit
**Triggers:** after editing any `.py` file
**Runs:** `ruff check` + `ruff format --check` on the changed file
**Output:** lint errors appear immediately in Claude's context so it can fix them before continuing

### post_ts_edit
**Triggers:** after editing any `.ts` or `.tsx` file
**Runs:** `tsc --noEmit` on the frontend
**Output:** type errors appear immediately — no waiting until the build step

### post_edit_test
**Triggers:** after editing any `.py` file
**Runs:** the corresponding unit test file if it exists (`tests/unit/test_<module>.py`)
**Why:** instant red/green feedback without running the full suite

---

## Agents

Specialist agents in `.claude/agents/`. Invoke from Claude with:
```
"run the security-auditor agent on this PR"
"use the migration-validator agent to check my new migration"
```

Or use the `Agent` tool directly in Claude Code.

### security-auditor
Reviews auth flows, token handling, JWT config, API endpoints, and CORS.
**When to use:** before any changes to `auth/`, `garmin/`, or when adding new API routes. Always run on PRs that touch security-sensitive code.

### schema-sync
Audits Pydantic backend response schemas vs TypeScript frontend types for field drift.
**When to use:** after any backend schema change, before opening a PR.

### migration-validator
Validates Alembic migration files for SQLite/PostgreSQL safety — checks `render_as_batch`, naive datetimes, `batch_alter_table` usage.
**When to use:** after writing a new migration, before committing.

### dependency-auditor
Runs `pip-audit` (backend) and `npm audit` (frontend), reports combined findings sorted by severity.
**When to use:** before any release, or on a weekly cadence.

### e2e-test-writer
Writes Playwright E2E tests for critical user journeys. Works alongside the Playwright MCP for real browser observation.
**When to use:** when adding a new user-facing feature that needs end-to-end coverage.

### backend-dev / frontend-dev / reviewer / infra
Pre-existing specialist agents for parallel feature work — see `CLAUDE.md` Agents section.

---

## Skills (Slash Commands)

Skills are invoked via the `Skill` tool or as `/skill-name` in the chat.

### /garmin-429-debug
Diagnoses and fixes Garmin SSO 429 / Akamai bot-detection errors.
Triggers automatically when Garmin connect fails with 429, GarthHTTPError, or sso.garmin.com errors.
Walks through: log analysis → `test_garmin_login.py` comparison → `_ChromeTLSSession` fix → Chrome version bump if needed.

```
"garmin connect is returning 429 in production"
"getting GarthHTTPError on login"
```

### /alembic-migration
Scaffolds a new Alembic migration with safety checks (render_as_batch, naive datetime, SQLite compat).

```
"/alembic-migration add garmin_device column to athlete_profile"
```

### /api-contract-check
Audits Pydantic schemas vs TypeScript types for field drift.
Run after any backend schema change.

### /coverage-gate
Runs backend (`pytest --cov`) and frontend (`vitest --coverage`) and fails if below threshold (80%).
Integrated into `/ship` step 1 — runs automatically.

### /env-var-audit
Audits env var drift across `config.py`, `.env.example`, `docker-compose.yml`, and `render.yaml`.
Run when adding new settings or before a release.

### /new-feature
Scaffolds a new feature: creates `features/<name>/PLAN.md`, `features/<name>/CLAUDE.md`, updates `STATUS.md` and root `PLAN.md`.

```
"/new-feature pace-predictor"
```

### /ship
Full ship workflow:
1. Run coverage gate
2. Code review (5-agent)
3. Generate fix prompt for issues found
4. Local test steps
5. Update docs (wrap-up-docs-check)
6. Open PR

### /release
Release workflow:
1. Pre-flight checks
2. Run tests
3. Security review
4. Version bump (`frontend/package.json`)
5. Update + commit STATUS.md (marks release ✅, adds entry to Infrastructure table)
6. Tag + push — tag lands on the STATUS.md commit
7. GitHub Actions: tests → approval gate → GitHub Release → Render deploy

---

## CI Changes (vs before this PR)

| Check | Before | After |
|---|---|---|
| Backend tests | pytest | pytest (unchanged) |
| Backend deps | — | pip-audit (ignores CVE-2024-23342) |
| Frontend tests | vitest + build | vitest + build (unchanged) |
| Frontend deps | npm audit --high | npm audit --moderate (stricter) |

---

## Credential Setup (Desktop App)

The Claude Code desktop app does **not** read `~/.zshrc`, so env var placeholders in `.mcp.json` are always empty. The solution is `.mcp.json.local` (gitignored) with hardcoded credentials.

```json
// .mcp.json.local  (gitignored — never commit this)
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql+asyncpg://...?ssl=require"]
    }
  }
}
```

After creating/updating `.mcp.json.local`, **restart Claude Code** — MCP servers are spawned at session start and don't hot-reload.

**Worktrees**: each worktree has its own `.mcp.json` (env-var template). You need a separate local override per worktree, or copy `.mcp.json.local` from the project root into the worktree directory.
