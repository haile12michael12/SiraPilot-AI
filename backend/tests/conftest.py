import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
import app.models

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/sirapilot_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-with-more-than-thirty-two-characters")
os.environ.setdefault("APP_ENV", "test")

from app.main import create_app


@pytest.fixture
def test_engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    engine.dispose()


@pytest.fixture
def client(test_engine: Engine) -> TestClient:
    Base.metadata.create_all(test_engine)
    application = create_app(engine=test_engine)
    with TestClient(application) as test_client:
        yield test_client
