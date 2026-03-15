from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.api.dependencies import get_current_user
from app.crud.game import GameCRUD
from app.db.models.user import User

router = APIRouter(prefix="/game", tags=["Game"])


@router.websocket("/ws/{lobby_id}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: int, current_user: User = Depends(get_current_user)):
    # Проверяем, участвует ли пользователь в этой игре
    game_user = await GameCRUD.get_game_user(game_id=lobby_id, user_id=current_user.id)

    if not game_user:
        await websocket.close(code=4003)  # Forbidden
        return

    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            # Обработка игровых данных (базовая заглушка)
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        # Тут можно добавить логику отключения игрока
        pass
