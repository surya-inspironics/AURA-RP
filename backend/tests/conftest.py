import os
import tempfile
import time
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url


_APP_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./aura.db")
_TEMP_ROOT = tempfile.TemporaryDirectory(prefix="aura-test-")
_TEMP_ROOT_PATH = Path(_TEMP_ROOT.name).resolve()


def _sqlite_path(database_url: str) -> Path | None:
    try:
        parsed_url = make_url(database_url)
    except Exception:
        return None
    if parsed_url.get_backend_name() != "sqlite" or not parsed_url.database:
        return None
    if parsed_url.database == ":memory:":
        return None
    return Path(parsed_url.database).resolve()


def _validate_test_database_url(database_url: str, app_database_url: str) -> Path:
    test_path = _sqlite_path(database_url)
    if test_path is None:
        raise RuntimeError("AURA_TEST_DATABASE_URL must identify a disposable SQLite file.")

    app_path = _sqlite_path(app_database_url)
    if app_path is not None and test_path == app_path:
        raise RuntimeError("The test database must be separate from the configured application database.")

    temp_root = Path(tempfile.gettempdir()).resolve()
    if not test_path.is_relative_to(temp_root) or not test_path.name.startswith("aura_test_"):
        raise RuntimeError("The test database must be an aura_test_ SQLite file inside the system temporary directory.")
    if not test_path.parent.exists():
        raise RuntimeError("The disposable test database directory must already exist.")
    if test_path.exists():
        raise RuntimeError("The configured disposable test database already exists; refusing to reuse it.")
    return test_path


def _reject_external_test_database_url(configured_url: str | None) -> None:
    if configured_url:
        raise RuntimeError("AURA_TEST_DATABASE_URL is managed by pytest and cannot be overridden.")


_requested_test_database_url = os.environ.get("AURA_TEST_DATABASE_URL")
if _requested_test_database_url:
    _TEMP_ROOT.cleanup()
    _reject_external_test_database_url(_requested_test_database_url)

_TEST_DATABASE_PATH = _TEMP_ROOT_PATH / f"aura_test_{os.urandom(8).hex()}.sqlite3"
_TEST_DATABASE_URL = make_url(
    "sqlite://",
).set(database=str(_TEST_DATABASE_PATH)).render_as_string(hide_password=False)
_validate_test_database_url(_TEST_DATABASE_URL, _APP_DATABASE_URL)

os.environ["AURA_TEST_DATABASE_URL"] = _TEST_DATABASE_URL
os.environ["DATABASE_URL"] = _TEST_DATABASE_URL
os.environ["STORAGE_DIR"] = str(_TEMP_ROOT_PATH / "evidence")
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture(autouse=True)
def isolated_test_state(monkeypatch):
    from backend.app.database.seed import seed_initial_data
    from backend.app.database.session import Base, SessionLocal, engine
    from backend.app.gold_loan.integrations.base import IntegrationMode
    from backend.app.gold_loan.integrations.registry import adapter_registry
    import backend.app.gold_loan.integrations.payment_gateway_adapter as payment_adapter_module
    import httpx

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()

    for adapter in adapter_registry._adapters.values():
        adapter.mode = IntegrationMode.SANDBOX
        adapter.clear_simulation()
        adapter.last_error = None

    adapter_registry.disbursal.disbursals.clear()
    adapter_registry.disbursal.idempotency_keys.clear()
    adapter_registry.device_gateway.used_nonces.clear()

    def block_unmocked_network(*args, **kwargs):
        raise AssertionError("External network access is disabled in backend tests.")

    monkeypatch.setattr(httpx, "get", block_unmocked_network)
    monkeypatch.setattr(payment_adapter_module, "urlopen", block_unmocked_network)

    gold_rates = adapter_registry.gold_rate
    fixture_rates = {"24K": 750000, "22K": 687000, "18K": 562500}

    def use_static_gold_rate_fixture():
        with gold_rates._lock:
            gold_rates._cached_rates = dict(fixture_rates)
            gold_rates._cache_time = time.time()
            gold_rates._rate_version = "TEST-FIXTURE"
            gold_rates._last_source = "STATIC_FALLBACK"

    monkeypatch.setattr(gold_rates, "_refresh_cache", use_static_gold_rate_fixture)
    use_static_gold_rate_fixture()

    try:
        yield
    finally:
        Base.metadata.drop_all(bind=engine)


def pytest_unconfigure(config):
    from sys import modules

    session_module = modules.get("backend.app.database.session")
    if session_module is not None:
        session_module.engine.dispose()

    _TEMP_ROOT.cleanup()
