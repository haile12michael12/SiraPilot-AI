from unittest.mock import Mock

from sqlalchemy.exc import OperationalError


def test_liveness(client) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_database_connectivity(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_readiness_reports_database_failure(client) -> None:
    client.app.state.db_engine = Mock()
    client.app.state.db_engine.connect.side_effect = OperationalError(
        "SELECT 1",
        {},
        OSError("database unavailable"),
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "database": "unavailable",
    }
