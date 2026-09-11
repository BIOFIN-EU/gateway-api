import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.settings import settings
from app.logging_config import setup_logging
from app.routers.endpoints import api_router


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.physical_client = httpx.AsyncClient(
        base_url=settings.PHYSICAL_API_URL,
        follow_redirects=True,
        timeout=30.0,
    )
    app.state.auth_client = httpx.AsyncClient(
        base_url=settings.AUTH_URL,
        follow_redirects=True,
        timeout=30.0,
    )
    app.state.risk_client = httpx.AsyncClient(
        base_url=settings.RISK_API_URL,
        follow_redirects=True,
        timeout=30.0,
    )

    logger.info("Started upstream http clients")
    yield
    await app.state.physical_client.aclose()
    await app.state.auth_client.aclose()
    await app.state.risk_client.aclose()
    logger.info("Closed upstream http clients")


app = FastAPI(
    title="Gateway API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )

    remote_services = [
        ("physical", settings.PHYSICAL_API_URL, ""),
        ("auth", settings.AUTH_URL, ""),
        ("risk", settings.RISK_API_URL, ""),
    ]

    for service_name, base_url, prefix in remote_services:
        try:
            with httpx.Client(base_url=base_url, timeout=10.0) as client:
                remote_schema = client.get("/openapi.json").json()

            schema.setdefault("paths", {})
            for path, path_item in remote_schema.get("paths", {}).items():
                schema["paths"][f"{prefix}{path}"] = path_item

            schema.setdefault("components", {})
            for section, values in remote_schema.get("components", {}).items():
                schema["components"].setdefault(section, {})
                schema["components"][section].update(values)

            logger.info("Merged %s OpenAPI schema successfully", service_name)

        except Exception as exc:
            logger.warning("Could not merge %s OpenAPI schema: %s", service_name, exc)

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
