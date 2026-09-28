from fastapi.testclient import TestClient

from server.rest_api import app, store


client = TestClient(app)

def setup_function():
    store._cache = type(store._cache)(capacity=store._cache.capacity)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_set_and_get_key():
    response = client.put(
        "/keys/name",
        json={"value": "Jiya"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "stored"

    response = client.get("/keys/name")

    assert response.status_code == 200
    assert response.json() == {
        "key": "name",
        "value": "Jiya",
    }


def test_get_missing_key():
    response = client.get("/keys/missing")

    assert response.status_code == 404


def test_delete_key():
    client.put(
        "/keys/name",
        json={"value": "Jiya"},
    )

    response = client.delete("/keys/name")

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    response = client.get("/keys/name")
    assert response.status_code == 404


def test_exists():
    client.put(
        "/keys/name",
        json={"value": "Jiya"},
    )

    response = client.get("/keys/name/exists")

    assert response.status_code == 200
    assert response.json() == {
        "key": "name",
        "exists": True,
    }


def test_keys():
    client.put(
        "/keys/name",
        json={"value": "Jiya"},
    )

    response = client.get("/keys")

    assert response.status_code == 200
    assert response.json() == {
        "keys": ["name"],
    }


def test_stats():
    response = client.get("/stats")

    assert response.status_code == 200
    assert "size" in response.json()
    assert "capacity" in response.json()