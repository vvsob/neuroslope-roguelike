from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.crud.character import CharacterCRUD
from app.db.models.user import User

router = APIRouter(prefix="/lobby", tags=["Lobby"])


@router.get("/me")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    characters = await CharacterCRUD.characters_list()

    return {
        "id": current_user.id,
        "name": current_user.name,
        "characters": characters
    }
