import logging
from fastapi import FastAPI, Request
from app.routers.endpoints import api_router
from fastapi.middleware.cors import CORSMiddleware
from app.logging_config import setup_logging
from fastapi.security import OAuth2PasswordBearer


setup_logging()
logger = logging.getLogger(__name__)


app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


app.include_router(api_router)


# # start up httpx services
#
# @app.on_event("startup")
# async def startup_event():
#     for service in all_services:
#         await service.start()
#     print("✅ All ApiService clients started")
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     for service in all_services:
#         await service.close()
#     print("🛑 All ApiService clients closed")
