# Database + API — CLAUDE

## Integration Test conftest.py Pattern

```python
import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.dependencies import get_session

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

## Gotchas

- **JSON columns**: Store WorkoutStep lists as JSON text. Use Pydantic for
  serialization, not raw `json.loads`.
- **Zone cascade**: Most complex flow. Test the full chain:
  recalc zones → re-resolve workouts → mark modified → optionally re-sync.
- **Thin routers**: Validate input and delegate. Business logic in services.
