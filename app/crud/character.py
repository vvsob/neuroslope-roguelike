import uuid

from sqlalchemy import select
from app.db import Base, async_session_maker
from app.db.models import Character


class CharacterCRUD:
    @staticmethod
    async def characters_list():
        async with async_session_maker() as session:
            result = await session.execute(
                select(Character)
            )
            characters = result.scalars().all()

        return [
            {
                "id": character.id,
                "name": character.name,
                "health": character.health,
            }
            for character in characters
        ]

    @staticmethod
    async def get_character_by_id(character_id: int):
        async with async_session_maker() as session:
            result = await session.execute(
                select(Character).where(Character.id == character_id)
            )
            character = result.scalar_one_or_none()

        return character
