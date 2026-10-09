"""
What the gateway lets through to the internal services, and what it tells
them about the caller.
"""
from __future__ import annotations

import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app

USER_ID = str(uuid.uuid4())


def _token(user_id: str = USER_ID, secret: str = "jwt-secret") -> str:
    return jwt.encode({"sub": user_id, "roles": ["user"], "permissions": []}, secret, algorithm="HS256")


@pytest.fixture
def upstream():
    """Upstream services that record each request and answer 200."""
    calls: list[tuple[str, httpx.Request]] = []

    def service(name: str, status: int = 200):
        def handle(request: httpx.Request) -> httpx.Response:
            calls.append((name, request))
            return httpx.Response(status, json={"ok": True})
        return httpx.AsyncClient(transport=httpx.MockTransport(handle), base_url=f"http://{name}")

    def install(physical_status: int = 200):
        app.state.physical_client = service("physical", physical_status)
        app.state.auth_client = service("auth")
        app.state.risk_client = service("risk")

    install()
    return calls, install


@pytest.fixture
def client():
    return TestClient(app)


# ---------- physical-api ----------

def test_physical_requests_carry_the_user_and_the_secret(client, upstream):
    calls, _ = upstream
    response = client.get(
        "/api/case_workflow/cases",
        headers={
            "Authorization": f"Bearer {_token()}",
            # A caller can't name another user or guess the secret.
            "X-User-Id": str(uuid.uuid4()),
            "X-Internal-Secret": "guess",
        },
    )
    assert response.status_code == 200
    (name, request), = calls
    assert name == "physical"
    assert request.headers.get_list("x-user-id") == [USER_ID]
    assert request.headers.get_list("x-internal-secret") == ["internal-secret"]


def test_physical_requests_need_a_valid_token(client, upstream):
    calls, _ = upstream
    assert client.get("/api/case_workflow/cases").status_code == 401
    forged = _token(secret="not-the-key")
    assert client.get("/api/case_workflow/cases", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    assert calls == []


def test_contact_form_is_open_but_names_no_user(client, upstream):
    calls, _ = upstream
    assert client.post("/api/support/contact", json={}).status_code == 200
    (_, request), = calls
    assert "x-user-id" not in request.headers
    assert request.headers["x-internal-secret"] == "internal-secret"


# ---------- auth-api ----------

@pytest.mark.parametrize("path", ["users/by-email?email=a@b.c", "users/anything", "login/../users/by-email"])
def test_internal_auth_endpoints_are_not_reachable(client, upstream, path):
    calls, _ = upstream
    assert client.get(f"/api/auth/{path}").status_code == 404
    assert calls == []


def test_public_auth_endpoints_pass_through(client, upstream):
    calls, _ = upstream
    assert client.post("/api/auth/login", json={"email": "a@b.c", "password": "x"}).status_code == 200
    assert [name for name, _ in calls] == ["auth"]


def test_closing_an_account_releases_its_projects_first(client, upstream):
    calls, _ = upstream
    response = client.post("/api/auth/close-account", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 200
    assert [(name, request.url.path) for name, request in calls] == [
        ("physical", "/api/account/close"),
        ("auth", "/api/auth/close-account"),
    ]
    assert calls[0][1].headers["x-user-id"] == USER_ID


def test_account_is_not_closed_if_its_projects_cannot_be_released(client, upstream):
    calls, install = upstream
    install(physical_status=500)
    response = client.post("/api/auth/close-account", headers={"Authorization": f"Bearer {_token()}"})
    assert response.status_code == 502
    assert [name for name, _ in calls] == ["physical"]  # auth-api never asked to close it
    assert "could not be closed" in json.loads(response.content)["detail"]


# ---------- risk framework ----------

def test_risk_framework_needs_a_user_or_physical_api(client, upstream):
    calls, _ = upstream
    assert client.get("/api/vulnerability/management-actions/get/1/").status_code == 401
    assert client.get(
        "/api/vulnerability/management-actions/get/1/", headers={"Authorization": f"Bearer {_token()}"}
    ).status_code == 200
    assert client.get(
        "/api/vulnerability/management-actions/get/1/", headers={"X-Internal-Secret": "internal-secret"}
    ).status_code == 200
    # The secret isn't passed on.
    assert all("x-internal-secret" not in request.headers for _, request in calls)


# ---------- request size ----------

def test_uploads_over_the_limit_are_refused_before_reaching_physical_api(client, upstream):
    from app.routers.physical_layer_proxy import MAX_REQUEST_BYTES

    calls, _ = upstream
    auth = {"Authorization": f"Bearer {_token()}"}
    url = "/api/case_workflow/cases/1/submit-file?field_name=supporting_document"

    small = client.post(url, headers=auth, files={"file": ("report.pdf", b"%PDF-1.4 small", "application/pdf")})
    assert small.status_code == 200 and len(calls) == 1

    big = b"0" * (MAX_REQUEST_BYTES + 1)
    response = client.post(url, headers=auth, files={"file": ("big.pdf", big, "application/pdf")})
    assert response.status_code == 413
    assert response.json()["detail"] == "The upload is larger than 20 MB."

    # Without a declared length (a streamed body), the limit still holds.
    def chunks():
        for _ in range(22):
            yield b"0" * (1024 * 1024)
    response = client.post(url, headers=auth, content=chunks())
    assert response.status_code == 413
    assert len(calls) == 1
