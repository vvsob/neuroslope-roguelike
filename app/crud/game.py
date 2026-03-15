from app.db import Base, async_session_maker
from app.db.models import *


class GameCRUD:
    @staticmethod
    async def create_game(user_id: int, character_id: int) -> Game:
        async with async_session_maker() as session:
            game = Game()
            session.add(game)
            await session.commit()

            game_user = GameUser(
                game_id=game.id,
                user_id=user_id,
                character_id=character_id
            )
            session.add(game_user)
            await session.commit()

        return game
