"""
Requests the gateway makes on a user's behalf to internal services.

physical-api trusts the user the gateway names in X-User-Id, so those
headers, and the secret proving the request comes from the gateway, are
only ever set here: anything a caller sends under these names is dropped.
"""
from __future__ import annotations

import hmac

from fastapi import Request
from jose import JWTError, jwt

from app.core.settings import settings
from app.dependencies.user_auth import CurrentUser

INTERNAL_SECRET_HEADER = "X-Internal-Secret"

# Lower-case: compared with incoming header names.
GATEWAY_ONLY_HEADERS = {"x-user-id", "x-user-roles", "x-user-permissions", "x-internal-secret"}


def user_from_token(token: str | None) -> CurrentUser | None:
    """The user a valid access token is for; None if missing or invalid."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return CurrentUser(user_id, payload.get("roles", []), payload.get("permissions", []))


def internal_headers(user: CurrentUser | None) -> dict[str, str]:
    headers = {INTERNAL_SECRET_HEADER: settings.INTERNAL_API_SECRET}
    if user is not None:
        headers["X-User-Id"] = str(user.user_id)
        headers["X-User-Roles"] = ",".join(user.roles or [])
        headers["X-User-Permissions"] = ",".join(user.permissions or [])
    return headers


def has_internal_secret(request: Request) -> bool:
    """A request from an internal service (physical-api), not a user."""
    sent = request.headers.get(INTERNAL_SECRET_HEADER)
    return bool(sent) and hmac.compare_digest(sent.encode(), settings.INTERNAL_API_SECRET.encode())
