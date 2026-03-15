from sqlalchemy import select
from app.db import Base, async_session_maker
from app.db.models import *


class GameCRUD:
    @staticmethod
    async def create_game(user_id: int, character_id: int) -> tuple[Game, GameUser]:
        async with async_session_maker() as session:
            game = Game()
            session.add(game)
            await session.commit()
            await session.refresh(game)

            game_user = GameUser(
                game_id=game.id,
                user_id=user_id,
                character_id=character_id
            )
            session.add(game_user)
            await session.commit()
            await session.refresh(game_user)

        return game, game_user

    @staticmethod
    async def get_game_user(game_id: int, user_id: int) -> Optional[GameUser]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(GameUser).where(
                    GameUser.game_id == game_id,
                    GameUser.user_id == user_id
                )
            )
            return result.scalar_one_or_none()
