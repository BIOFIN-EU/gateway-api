import logging
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth_client import (
    register_user,
    login_user,
    refresh_token,
    get_me,
)

# 🔽 import schemas from gateway
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()

bearer_scheme = HTTPBearer()


# -------------------------
# REGISTER
# -------------------------
@router.post("/register", response_model=UserOut)
async def register(payload: RegisterRequest):
    logger.info("Gateway: register request")
    return await register_user(payload)


# -------------------------
# LOGIN
# -------------------------
@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest):
    logger.info("Gateway: login request")
    return await login_user(payload)


# -------------------------
# REFRESH
# -------------------------
@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest):
    logger.info("Gateway: refresh request")
    return await refresh_token(payload)


# -------------------------
# ME
# -------------------------
@router.get("/me", response_model=UserOut)
async def me(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    logger.info("Gateway: me request")
    token = creds.credentials
    return await get_me(token)
