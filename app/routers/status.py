import logging
from fastapi import APIRouter, Depends
from app.deps.user_auth import CurrentUser, require_user, require_role, require_permission

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api_status")
async def get_api_status():
    return {"status": "OK"}


@router.get("/profile")
async def profile(user = Depends(require_user)):
    return {"email": user.email}


@router.post("/admin/create")
async def create_admin(
    user = Depends(require_role("admin"))
):
    return {"ok": True,
            "email": user.email}

@router.post("/roles")
async def create_role(
    user = Depends(require_permission("roles:write"))
):
    return {"ok": True,
            "email": user.email}