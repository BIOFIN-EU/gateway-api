import httpx
import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.settings import settings
from app.dependencies.user_auth import CurrentUser

# Paths (relative to this router's /api mount, i.e. without a leading /api/)
# that the /support contact form needs to reach without being logged in.
# Everything else on this proxy still requires a valid user token.
PUBLIC_PROXY_PATHS = {"support/contact"}

optional_bearer = HTTPBearer(auto_error=False)

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}

TRUSTED_IDENTITY_HEADERS = {
    "x-user-id",
    "x-user-roles",
    "x-user-permissions",
}

router = APIRouter()


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def physical_layer_reverse_proxy(
    path: str,
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
):
    is_public_path = path in PUBLIC_PROXY_PATHS

    current_user: CurrentUser | None = None

    if creds:
        try:
            payload = jwt.decode(
                creds.credentials,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            user_id = payload.get("sub")
            if user_id:
                current_user = CurrentUser(
                    user_id,
                    payload.get("roles", []),
                    payload.get("permissions", []),
                )
        except JWTError:
            current_user = None

    if current_user is None and not is_public_path:
        raise HTTPException(status_code=401, detail="Not authenticated")

    client: httpx.AsyncClient = request.app.state.physical_client

    upstream_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() not in TRUSTED_IDENTITY_HEADERS
    }

    if current_user:
        logger.debug(f"UUID = {current_user.user_id}, Roles = {current_user.roles}, Permissions = {current_user.permissions}")

        upstream_headers["X-User-Id"] = str(current_user.user_id)
        upstream_headers["X-User-Roles"] = ",".join(current_user.roles or [])
        upstream_headers["X-User-Permissions"] = ",".join(current_user.permissions or [])

    body = await request.body()

    upstream_response = await client.request(
        method=request.method,
        url=f"/api/{path}",
        params=request.query_params,
        headers=upstream_headers,
        content=body,
    )

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )