from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.settings import settings

bearer_scheme = HTTPBearer(auto_error=True)


class CurrentUser:
    def __init__(
        self,
        user_id: str,
        email: str | None,
        roles: List[str],
        permissions: List[str],
    ):
        self.user_id = user_id
        self.email = email
        self.roles = roles
        self.permissions = permissions


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    token = creds.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        user_id = payload.get("sub")
        email = payload.get("email")
        roles = payload.get("roles", [])
        permissions = payload.get("permissions", [])

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        return CurrentUser(
            user_id=user_id,
            email=email,
            roles=roles,
            permissions=permissions,
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def require_role(role: str):
    def _dep(user: CurrentUser = Depends(get_current_user)):
        if role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: role required",
            )
        return user
    return _dep


def require_permission(permission: str):
    def _dep(user: CurrentUser = Depends(get_current_user)):
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: permission required",
            )
        return user
    return _dep


async def require_user(user: CurrentUser = Depends(get_current_user)):
    return user