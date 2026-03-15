from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.db import User

router = APIRouter(prefix="/lobby", tags=["Lobby"])


@router.get("/me")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name
    }
