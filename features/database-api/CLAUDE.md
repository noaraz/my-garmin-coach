# Database + API — CLAUDE

## Architecture

```
routers/          ← async def route handlers (thin — validate + delegate)
services/         ← async class-based singletons (business logic)
repositories/     ← async BaseRepository[T] (data access layer)
db/models.py      ← SQLModel tables
db/database.py    ← async engine + AsyncSession factory
core/config.py    ← BaseSettings (pydantic-settings, @lru_cache)
```

## Integration Test conftest.py Pattern

```python
# tests/integration/conftest.py — respects TEST_DATABASE_URL for PostgreSQL
_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
_IS_SQLITE = _TEST_DB_URL.startswith("sqlite")

@pytest.fixture(name="session")
async def session_fixture():
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    if _IS_SQLITE:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    # PostgreSQL: alembic migrations run via session-scoped _setup_db_schema fixture
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_factory() as session:
        yield session
    await engine.dispose()

@pytest.fixture(name="client")
async def client_fixture(session: AsyncSession):
    app = create_app()
    async def override_session():
        yield session
    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

For routes that also need `get_sync_service` overridden (e.g. sync tests), add:
```python
app.dependency_overrides[get_sync_service] = lambda: mock_sync_service
```

## Service Class Pattern

Services are async class singletons. Module-level shims keep router imports stable:

```python
class ProfileService:
    async def get_or_create(self, session: AsyncSession) -> AthleteProfile: ...
    async def update(self, session: AsyncSession, data: dict) -> AthleteProfile: ...

profile_service = ProfileService()

# shims
async def get_or_create_profile(session): return await profile_service.get_or_create(session)
async def update_profile(session, data): return await profile_service.update(session, data)
```

## Repository Pattern

```python
class BaseRepository(Generic[ModelType]):
    async def get(self, session, id) -> ModelType | None: ...
    async def get_all(self, session) -> list[ModelType]: ...
    async def create(self, session, obj) -> ModelType: ...
    async def delete(self, session, obj) -> None: ...

class ProfileRepository(BaseRepository[AthleteProfile]):
    async def get_singleton(self, session) -> AthleteProfile | None: ...

profile_repository = ProfileRepository(AthleteProfile)
```

## Async Session Operations

```python
# queries
result = await session.exec(select(Model).where(...))
rows = result.all()
obj = result.first()

# by pk
obj = await session.get(Model, pk)

# mutations
session.add(obj)          # sync — no await
await session.commit()
await session.refresh(obj)
await session.delete(obj)
```

## Gotchas

- **Async engine**: `create_async_engine` + `sqlite+aiosqlite://` URL. `check_same_thread` not needed.
- **Table creation**: `async with engine.begin() as conn: await conn.run_sync(SQLModel.metadata.create_all)`
- **`expire_on_commit=False`**: Required on `sessionmaker` for async — avoids lazy-load errors after commit.
- **JSON columns**: Store WorkoutStep lists as JSON text. Use Pydantic for serialization.
- **Zone cascade**: Most complex flow. `recalculate_hr_zones` → `_cascade_re_resolve` → re-resolve **all incomplete** workouts (not just future ones) → mark `sync_status='modified'`.
- **Cascade date filter gotcha**: Never use `date >= today` in zone or template cascades. Use `get_all_incomplete()` (no date filter, only `completed == False`). A workout scheduled for yesterday that is already "synced" must still be re-marked "modified" when zones change — otherwise `sync_all` finds nothing to push.
- **`user_id` on ScheduledWorkout**: Must be set at creation via `user_id=profile.user_id`. Without it, user-scoped queries silently miss the workout.
- **Thin routers**: Validate input, `await` service calls, return response model. No business logic in routers.
- **API prefix**: All routes under `/api/v1/`. Health check at `/api/v1/health`.
- **CORS**: Configured in `create_app()` via `CORSMiddleware`. Origins read from `Settings.cors_origins`.
