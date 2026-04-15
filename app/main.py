import logging
import httpx

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer

from app.routers.endpoints import api_router
from app.logging_config import setup_logging


setup_logging()
logger = logging.getLogger(__name__)

REMOTE_SERVICE_URL = "http://physical-api:8020"
REMOTE_PREFIX = ""

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        base_url=REMOTE_SERVICE_URL,
        follow_redirects=True,
        timeout=30.0,
    )
    logger.info("Started proxy http client")
    yield
    await app.state.http_client.aclose()
    logger.info("Closed proxy http client")


app = FastAPI(
    title="Gateway API",
    lifespan=lifespan,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.api_route(
    f"{REMOTE_PREFIX}" + "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    include_in_schema=False
)
async def reverse_proxy(path: str, request: Request):
    client: httpx.AsyncClient = request.app.state.http_client

    upstream_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    body = await request.body()

    upstream_response = await client.request(
        method=request.method,
        url=f"/{path}",
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


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )

    # Try to pull in the remote service schema
    # This makes remote endpoints show up in THIS app's Swagger UI.
    try:
        with httpx.Client(base_url=REMOTE_SERVICE_URL, timeout=10.0) as client:
            remote_schema = client.get("/openapi.json").json()

        schema.setdefault("paths", {})
        for path, path_item in remote_schema.get("paths", {}).items():
            schema["paths"][f"{REMOTE_PREFIX}{path}"] = path_item

        # Merge components
        schema.setdefault("components", {})
        for section, values in remote_schema.get("components", {}).items():
            schema["components"].setdefault(section, {})
            schema["components"][section].update(values)

        logger.info("Merged remote OpenAPI schema successfully")

    except Exception as exc:
        logger.warning("Could not merge remote OpenAPI schema: %s", exc)

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi