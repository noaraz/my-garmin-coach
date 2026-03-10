# RELEASING.md — GarminCoach Release Process

## Versioning

Semantic versioning: `vMAJOR.MINOR.PATCH`

| Bump | When | Migration needed? |
|------|------|------------------|
| `PATCH` | Bug fixes, no schema change | No |
| `MINOR` | New features, backward-compatible | Maybe |
| `MAJOR` | Breaking API or schema changes | Yes |

---

## Pre-Release Checklist

1. All features for the release are merged to `main`
2. Tests pass: `docker compose exec backend pytest -v`
3. Security review complete (`/code-review` on auth, tokens, CORS, routes)
4. No secrets in code or git history
5. If schema changed: migration created, tested locally, and applied on Render before deploy

---

## GitHub Actions Workflows

| Workflow | File | Trigger | What it does |
|---|---|---|---|
| CI | `.github/workflows/ci.yml` | Push to `main` or PR | Backend tests + lint, frontend tests + build |
| Release | `.github/workflows/release.yml` | Tag `v*.*.*` pushed | Security checks + tests → creates GitHub Release |

**The release workflow is the security gate.** Pushing a tag triggers:
1. Full test suite (backend pytest + frontend vitest + tsc build)
2. Python SAST (`bandit` — medium+ severity)
3. Python CVE audit (`pip-audit`)
4. Frontend CVE audit (`npm audit --audit-level=high`)
5. Git history secret scan (`gitleaks`)

If any step fails, the GitHub Release is **not** created.

---

## Release Workflow

```bash
# 1. Ensure main is up to date
git checkout main && git pull

# 2. Tag the release — this triggers the security gate automatically
git tag -a v1.0.0 -m "Initial production release"

# 3. Push the tag → GitHub Actions runs security review → creates GitHub Release
git push origin v1.0.0

# (optional) manually create release with custom notes instead of auto-generated:
gh release create v1.0.0 \
  --title "v1.0.0 — Initial production release" \
  --notes "$(cat <<'EOF'
## What's in this release
- Full training platform: calendar, workout builder, zone management
- Garmin Connect sync (schedule, auto-sync on zone/profile change)
- Auth: JWT login, invite-only registration, Garmin token encryption

## Migration required
No — first deploy creates schema fresh via create_all()

## How to deploy
1. Connect GitHub repo to Render dashboard (first time only)
2. Render auto-deploys from render.yaml on push to main
3. After first startup: run `python -m alembic stamp head` in Render shell
EOF
)"
```

---

## Render Deploy + Stamp (first release only)

After the Render service is live and the first deploy completes:

```bash
# In Render shell (Dashboard → Shell tab)
cd /app && python -m alembic stamp head
```

This one-time step syncs Alembic's revision tracking with the DB that `create_all()` created on startup. All future deploys use `alembic upgrade head` if there's a schema change.

---

## Future Releases

```bash
# If schema changed — apply migration on Render BEFORE pushing code
# (in Render shell)
python -m alembic upgrade head

# Then tag and release as above
git tag -a v1.1.0 -m "Add zone test tagging"
git push origin v1.1.0
gh release create v1.1.0 --title "v1.1.0 — ..." --notes "..."
```
