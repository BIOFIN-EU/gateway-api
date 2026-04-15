from fastapi import APIRouter
from app.routers import status, auth


api_router = APIRouter()

std_prefix = '/api'

api_router.include_router(status.router,
                          prefix=f"{std_prefix}/status",
                          tags=["API Status"])

api_router.include_router(auth.router,
                          prefix=f"{std_prefix}/auth",
                          tags=["Authorisation"])

