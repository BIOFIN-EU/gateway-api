from fastapi import Depends, HTTPException, status
import httpx
from app.core.settings import settings
from app.deps.user_auth import get_current_user


def require_permission(permission: str):

    async def _dep(user=Depends(get_current_user)):

        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{settings.AUTH_SERVICE_URL}/rbac/check",
                params={"permission": permission, "email": user["email"]},
                headers={
                    "X-Client-ID": settings.AUTH_CLIENT_ID,
                    "X-Client-Secret": settings.AUTH_CLIENT_SECRET,
                },
            )

        if r.status_code != 200:
            raise HTTPException(status_code=403, detail="Forbidden")

        return user