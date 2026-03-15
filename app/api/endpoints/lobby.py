from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.crud.character import CharacterCRUD
from app.crud.game import GameCRUD
from app.db.models.user import User
from app.schemas.lobby import LobbyCreate

router = APIRouter(prefix="/lobby", tags=["Lobby"])


@router.get("/me")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    characters = await CharacterCRUD.characters_list()

    return {
        "id": current_user.id,
        "name": current_user.name,
        "characters": characters
    }


@router.post("/new-game")
async def create_new_game(lobby_data: LobbyCreate, current_user: User = Depends(get_current_user)):
    character = await CharacterCRUD.get_character_by_id(lobby_data.character_id)
    if character is None:
        return {"error": "Character not found"}

    game = await GameCRUD.create_game(user_id=current_user.id, character_id=character.id)

    return {
        "id": game.id
    }
