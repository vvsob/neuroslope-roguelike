from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.crud.character import CharacterCRUD
from app.db.models.user import User

router = APIRouter(prefix="/game", tags=["Game"])

@router.websocket("/ws")
async def websocket_endpoint(websocket, current_user: User = Depends(get_current_user)):
    pass