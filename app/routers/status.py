import logging
from fastapi import APIRouter, Depends

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api_status")
async def get_api_status():
    return {"status": "OK"}

