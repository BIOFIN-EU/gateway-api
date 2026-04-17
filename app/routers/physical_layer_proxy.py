import httpx
import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Request, Response

from app.dependencies.user_auth import CurrentUser, get_current_user

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
    current_user: CurrentUser = Depends(get_current_user),
):
    client: httpx.AsyncClient = request.app.state.physical_client

    upstream_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() not in TRUSTED_IDENTITY_HEADERS
    }

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