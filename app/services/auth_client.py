import httpx
from fastapi import HTTPException
from app.core.settings import settings

AUTH_URL = f"{settings.AUTH_URL}/api"


def _headers():
    return {
        "X-Client-ID": settings.AUTH_CLIENT_ID,
        "X-Client-Secret": settings.AUTH_CLIENT_SECRET,
    }


async def register_user(payload):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{AUTH_URL}/auth/register",
            json=payload.model_dump(),
            headers=_headers(),
        )
    if r.status_code != 201:
        raise HTTPException(
            status_code=r.status_code,
            detail=r.json().get("detail", r.text),
        )
    return r.json()


async def login_user(payload):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{AUTH_URL}/auth/login",
            json=payload.model_dump(),
            headers=_headers(),
        )
    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=r.json().get("detail", r.text),
        )
    return r.json()


async def refresh_token(payload):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{AUTH_URL}/auth/refresh",
            json=payload.model_dump(),
            headers=_headers(),
        )
    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=r.json().get("detail", r.text),
        )

    return r.json()


async def get_me(token: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{AUTH_URL}/auth/me",
            headers={
                **_headers(),
                "Authorization": f"Bearer {token}",
            },
        )
    if r.status_code != 200:
        raise HTTPException(
            status_code=r.status_code,
            detail=r.json().get("detail", r.text),
        )
    return r.json()
