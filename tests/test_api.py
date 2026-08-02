from collections.abc import Iterator

import pytest
from starlette.testclient import TestClient

from app.main import API_KEY, app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == "ok"


def test_sandbox_requires_api_key(client: TestClient) -> None:
    response = client.post(
        "/v1/sandbox/run",
        json={"language": "python3", "code": "print('blocked')"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == -401


def test_dify_python_contract_and_preload(client: TestClient) -> None:
    response = client.post(
        "/v1/sandbox/run",
        headers={"X-Api-Key": API_KEY},
        json={
            "language": "python3",
            "preload": "VALUE = 42",
            "code": "print(VALUE)",
            "enable_network": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "success",
        "data": {"error": "", "stdout": "42\n"},
    }


def test_python_error_uses_dify_response_schema(client: TestClient) -> None:
    response = client.post(
        "/v1/sandbox/run",
        headers={"X-Api-Key": API_KEY},
        json={"language": "python3", "code": "raise ValueError('bad input')"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"error": "bad input", "stdout": ""}
