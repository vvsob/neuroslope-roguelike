from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.db.session import get_session
from app.db.models.user import AuthToken, User

bearer_scheme = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        session: AsyncSession = Depends(get_session)
) -> User:
    token = credentials.credentials

    stmt = (
        select(AuthToken)
        .options(joinedload(AuthToken.user))
        .where(AuthToken.token == token)
    )
    result = await session.execute(stmt)
    auth_record = result.scalar_one_or_none()

    if not auth_record or not auth_record.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_record.user

