from fastapi import APIRouter
from app.routers import status, auth_proxy, physical_layer_proxy

api_router = APIRouter()

api_router.include_router(
    status.router,
    prefix="/status",
    tags=["API Status"],
)

api_router.include_router(
    auth_proxy.router,
    prefix="",
    tags=["Authorisation"],
)

api_router.include_router(
    physical_layer_proxy.router,
    prefix="",
    tags=["Physical Layer"],
)