import logging
import httpx

from fastapi import APIRouter, Request, Response
from app.core.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

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


def build_upstream_headers(request: Request) -> dict[str, str]:
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    headers["X-Client-ID"] = settings.AUTH_CLIENT_ID
    headers["X-Client-Secret"] = settings.AUTH_CLIENT_SECRET

    return headers


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def auth_reverse_proxy(path: str, request: Request):
    client: httpx.AsyncClient = request.app.state.auth_client

    upstream_headers = build_upstream_headers(request)
    body = await request.body()

    upstream_response = await client.request(
        method=request.method,
        url=f"/api/auth/{path}",
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