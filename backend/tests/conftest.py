import os

# Must be set before the app is imported. A fresh SQLite file per test session.
os.environ["DATABASE_URL"] = "sqlite:///./test_brightloop.db"
if os.path.exists("test_brightloop.db"):
    os.remove("test_brightloop.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # runs lifespan: creates tables + seeds the admin
        yield c


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client, email: str, password: str) -> dict:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return auth(r.json()["access_token"])


@pytest.fixture(scope="session")
def admin(client):
    return login(client, "admin@brightloop.com", "Admin@12345")
