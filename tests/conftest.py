"""
Shared pytest fixtures for Project Aura tests.

Key fixture: `engine` — a MemoryEngine backed by a per-test temporary
directory. Tests that read or write persistent memory must use this fixture
so they never touch the real data/memory/ directory.
"""
import pytest

from app.memory.engine import MemoryEngine
from app.memory.store import InMemorySessionMemoryStore, JsonFileMemoryStore


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """
    Redirect JsonFileMemoryStore I/O to a pytest-managed temporary directory.

    Monkeypatches the module-level _DATA_DIR in app.memory.store so that
    every JsonFileMemoryStore created during the test uses tmp_path.
    The directory is cleaned up automatically after each test.
    """
    monkeypatch.setattr("app.memory.store._DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def engine(tmp_data_dir):
    """
    MemoryEngine with fully isolated temporary storage.

    - Persistent store (user/relationship/episodic): writes to tmp_data_dir
    - Session store: in-memory dict, never touches disk
    """
    return MemoryEngine(
        session_store=InMemorySessionMemoryStore(),
        persistent_store=JsonFileMemoryStore(),
    )


@pytest.fixture
async def api_client():
    """
    Async HTTP client for FastAPI endpoint tests.

    Uses httpx.AsyncClient with ASGITransport — no real network calls.
    """
    from httpx import ASGITransport, AsyncClient

    from app.api.session import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
