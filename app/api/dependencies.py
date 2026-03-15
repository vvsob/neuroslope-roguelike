from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.requests import HTTPConnection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.db.session import get_session
from app.db.models.user import AuthToken, User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
        conn: HTTPConnection,
        session: AsyncSession = Depends(get_session)
) -> User:
    token = None
    auth_header = conn.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    if not token and conn.scope.get("type") == "websocket":
        token = conn.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
