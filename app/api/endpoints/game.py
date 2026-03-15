import enum

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.api.dependencies import get_current_user
from app.crud.game import GameCRUD
from app.db.models.user import User


class BattleType(enum.Enum):
    HALLWAY_FIGHT = "hallway_fight"
    ELITE_FIGHT = "elite_fight"
    CAMPFIRE = "campfire"
    TREASURE = "treasure"
    BOSS = "boss"

router = APIRouter(prefix="/game", tags=["Game"])


games_state = {}


@router.websocket("/ws/{lobby_id}")
async def websocket_endpoint(websocket: WebSocket, lobby_id: int, current_user: User = Depends(get_current_user)):
    # Проверяем, участвует ли пользователь в этой игре
    game_user = await GameCRUD.get_game_user(game_id=lobby_id, user_id=current_user.id)

    if not game_user:
        await websocket.close(code=4003)  # Forbidden
        return

    await websocket.accept()

    if lobby_id not in games_state:
        games_state[lobby_id] = {
            "map": [
                BattleType.HALLWAY_FIGHT,
                BattleType.HALLWAY_FIGHT,
                BattleType.CAMPFIRE,
                BattleType.ELITE_FIGHT,
                BattleType.BOSS
            ],
            "position_on_map": 0,
            "deck": [],
            "relics": [],
            "fight": None
        }

    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "play":
                if games_state[lobby_id]["fight"] is not None:
                    return {"error": "Already in a fight"}
                if games_state[lobby_id]["map"][games_state[lobby_id]["position_on_map"]] not in [BattleType.HALLWAY_FIGHT, BattleType.ELITE_FIGHT, BattleType.BOSS]:
                    return {"error": "No fight at current position"}


    except WebSocketDisconnect:
        # Тут можно добавить логику отключения игрока
        pass
