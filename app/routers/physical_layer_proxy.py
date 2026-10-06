import httpx
import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.internal import GATEWAY_ONLY_HEADERS, internal_headers, user_from_token

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

    current_user = user_from_token(creds.credentials if creds else None)

    if current_user is None and not is_public_path:
        raise HTTPException(status_code=401, detail="Not authenticated")

    client: httpx.AsyncClient = request.app.state.physical_client

    upstream_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() not in GATEWAY_ONLY_HEADERS
    }
    upstream_headers.update(internal_headers(current_user))

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