import logging
import httpx

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.core.internal import internal_headers, user_from_token
from app.core.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# The auth-api endpoints users may reach. Everything else (e.g. the email
# lookup physical-api uses) is internal; requests sent through here carry
# the gateway's client credentials, so they must not reach it.
PUBLIC_AUTH_PATHS = {
    "login",
    "register",
    "refresh",
    "logout",
    "me",
    "change-password",
    "close-account",
}

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
    if path not in PUBLIC_AUTH_PATHS:
        raise HTTPException(status_code=404, detail="Not Found")

    if path == "close-account" and request.method == "POST":
        refused = await release_projects_before_closing(request)
        if refused is not None:
            return refused

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

async def release_projects_before_closing(request: Request) -> Response | None:
    """
    Before an account is closed, physical-api hands its projects over to
    other members (or deletes those no one else can open) and removes its
    access. If that fails the account is not closed, so no project is left
    without anyone who can manage it. Returns the response to send instead
    of closing, or None to go ahead.
    """
    authorization = request.headers.get("authorization", "")
    token = authorization[7:] if authorization.lower().startswith("bearer ") else None
    user = user_from_token(token)
    if user is None:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    physical: httpx.AsyncClient = request.app.state.physical_client
    try:
        released = await physical.post("/api/account/close", headers=internal_headers(user))
    except httpx.HTTPError:
        logger.exception("Could not release the projects of user %s before closing", user.user_id)
        released = None

    if released is None or released.status_code >= 400:
        if released is not None:
            logger.error("physical-api refused to release user %s: %s", user.user_id, released.status_code)
        return JSONResponse(
            status_code=502,
            content={"detail": "Your account could not be closed right now. Please try again later."},
        )
    return None
