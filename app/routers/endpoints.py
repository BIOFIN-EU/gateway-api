from fastapi import APIRouter
from app.routers import status, auth_proxy, physical_layer_proxy

api_router = APIRouter()

api_router.include_router(
    status.router,
    prefix="/status",
    tags=["API Status"],
)

# More specific route first
api_router.include_router(
    auth_proxy.router,
    prefix="/api/auth",
    tags=["Authorisation"],
)

api_router.include_router(
    physical_layer_proxy.router,
    prefix="/api",
    tags=["Physical Layer"],
)