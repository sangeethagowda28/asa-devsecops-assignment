import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402

TEST_DB_URL = "sqlite:///./test_vulntracker.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register_and_login(username="alice", email="alice@example.com", password="password123"):
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    resp = client.post("/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_user():
    resp = client.post("/auth/register", json={
        "username": "bob",
        "email": "bob@example.com",
        "password": "secret",
    })
    assert resp.status_code == 201
    assert resp.json()["username"] == "bob"


def test_register_duplicate_username():
    payload = {"username": "bob", "email": "bob@example.com", "password": "secret"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json={**payload, "email": "bob2@example.com"})
    assert resp.status_code == 400


def test_login_success():
    client.post("/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "pw"})
    resp = client.post("/auth/login", json={"username": "alice", "password": "pw"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password():
    client.post("/auth/register", json={"username": "alice", "email": "alice@example.com", "password": "pw"})
    resp = client.post("/auth/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401


def test_create_scan():
    token = register_and_login()
    resp = client.post("/scans", json={
        "title": "Reflected XSS in search",
        "description": "User input is echoed without sanitisation",
        "severity": "high",
        "affected_component": "GET /search",
    }, headers=auth_headers(token))
    assert resp.status_code == 201
    assert resp.json()["title"] == "Reflected XSS in search"


def test_list_scans():
    token = register_and_login()
    client.post("/scans", json={
        "title": "Test finding",
        "severity": "low",
        "affected_component": "misc",
    }, headers=auth_headers(token))
    resp = client.get("/scans", headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_search_scans():
    # TODO: add assertions for search results
    token = register_and_login()
    client.post("/scans", json={
        "title": "SQL Injection via login",
        "severity": "critical",
        "affected_component": "POST /auth/login",
    }, headers=auth_headers(token))
    resp = client.get("/scans/search?q=SQL", headers=auth_headers(token))
    assert resp.status_code == 200


def test_update_scan_status():
    token = register_and_login()
    scan_id = client.post("/scans", json={
        "title": "Open redirect",
        "severity": "medium",
        "affected_component": "redirect handler",
    }, headers=auth_headers(token)).json()["id"]

    resp = client.patch(f"/scans/{scan_id}", json={"status": "in_progress"}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


def test_delete_scan():
    token = register_and_login()
    scan_id = client.post("/scans", json={
        "title": "Stale finding",
        "severity": "low",
        "affected_component": "misc",
    }, headers=auth_headers(token)).json()["id"]

    resp = client.delete(f"/scans/{scan_id}", headers=auth_headers(token))
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Shared Report Link tests (Task 1 feature)
# ---------------------------------------------------------------------------

def _create_scan(token):
    """Helper: create a scan and return its ID."""
    return client.post("/scans", json={
        "title": "XSS in dashboard",
        "severity": "high",
        "affected_component": "GET /dashboard",
    }, headers=auth_headers(token)).json()["id"]


def test_share_scan_returns_url():
    token = register_and_login()
    scan_id = _create_scan(token)
    resp = client.post(f"/scans/{scan_id}/share", json={}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert "share_url" in resp.json()
    assert "/share/" in resp.json()["share_url"]


def test_share_scan_with_password():
    token = register_and_login()
    scan_id = _create_scan(token)
    resp = client.post(
        f"/scans/{scan_id}/share",
        json={"password": "s3cret"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert "share_url" in resp.json()


def test_share_scan_not_found_for_other_owner():
    """A user cannot generate a share link for another user's scan."""
    token_a = register_and_login("alice2", "alice2@example.com", "pw")
    token_b = register_and_login("bob2", "bob2@example.com", "pw")
    scan_id = _create_scan(token_a)
    resp = client.post(f"/scans/{scan_id}/share", json={}, headers=auth_headers(token_b))
    assert resp.status_code == 404


def test_get_shared_scan_no_password():
    token = register_and_login()
    scan_id = _create_scan(token)
    share_url = client.post(
        f"/scans/{scan_id}/share", json={}, headers=auth_headers(token)
    ).json()["share_url"]
    share_token = share_url.split("/share/")[-1]
    resp = client.get(f"/share/{share_token}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "XSS in dashboard"


def test_get_shared_scan_correct_password():
    token = register_and_login()
    scan_id = _create_scan(token)
    share_url = client.post(
        f"/scans/{scan_id}/share",
        json={"password": "mysecret"},
        headers=auth_headers(token),
    ).json()["share_url"]
    share_token = share_url.split("/share/")[-1]
    resp = client.get(f"/share/{share_token}?password=mysecret")
    assert resp.status_code == 200
    assert resp.json()["title"] == "XSS in dashboard"


def test_get_shared_scan_wrong_password():
    token = register_and_login()
    scan_id = _create_scan(token)
    share_url = client.post(
        f"/scans/{scan_id}/share",
        json={"password": "correct"},
        headers=auth_headers(token),
    ).json()["share_url"]
    share_token = share_url.split("/share/")[-1]
    resp = client.get(f"/share/{share_token}?password=wrong")
    assert resp.status_code == 401


def test_get_shared_scan_missing_password():
    token = register_and_login()
    scan_id = _create_scan(token)
    share_url = client.post(
        f"/scans/{scan_id}/share",
        json={"password": "required"},
        headers=auth_headers(token),
    ).json()["share_url"]
    share_token = share_url.split("/share/")[-1]
    resp = client.get(f"/share/{share_token}")
    assert resp.status_code == 401


def test_get_shared_scan_invalid_token():
    resp = client.get("/share/nonexistent-token-abc123")
    assert resp.status_code == 404

