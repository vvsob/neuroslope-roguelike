import uuid

from app.db import Base, async_session_maker
from app.db.models import *


class UserCRUD:
    @staticmethod
    async def register(name: str) -> str:
        async with async_session_maker() as session:
            user = User(name=name)
            session.add(user)

            await session.commit()

            auth_token = AuthToken(user_id=user.id, token=str(uuid.uuid4()))
            session.add(auth_token)

            await session.commit()

        return auth_token.token
