import uuid

from app.db import Base, async_session_maker
from app.db.models import *


class CharacterCRUD:
    @staticmethod
    async def characters_list():
        async with async_session_maker() as session:
            result = await session.execute(
                Character.__table__.select()
            )
            characters = result.fetchall()

        return [
            {
                "id": character.id,
                "name": character.name,
            }
            for character in characters
        ]
