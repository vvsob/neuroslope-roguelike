from fastapi import APIRouter
from pydantic import BaseModel
from app.schemas.user import UserRegistration
from app.crud.user import UserCRUD

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
async def register(user: UserRegistration):
    token = await UserCRUD.register(user.name)
    return {"token": token}
