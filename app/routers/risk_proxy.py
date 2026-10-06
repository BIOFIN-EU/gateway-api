# app/routers/risk_proxy.py
import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from app.core.internal import GATEWAY_ONLY_HEADERS, has_internal_secret, user_from_token

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
    return {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
        and key.lower() not in GATEWAY_ONLY_HEADERS
    }


def is_allowed(request: Request) -> bool:
    """Signed-in users (the Vulnerability tab), and physical-api."""
    authorization = request.headers.get("authorization", "")
    token = authorization[7:] if authorization.lower().startswith("bearer ") else None
    return user_from_token(token) is not None or has_internal_secret(request)


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False,
)
async def risk_reverse_proxy(path: str, request: Request):
    # The framework's calculations are expensive: not open to anyone.
    if not is_allowed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    logger.debug(f"Proxying {request.method} risk-framework/{path} -> /api/v1/{path}")
    client: httpx.AsyncClient = request.app.state.risk_client

    upstream_headers = build_upstream_headers(request)
    body = await request.body()


    upstream_response = await client.request(
        method=request.method,
        url=f"/api/v1/{path}",
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
