from fastapi import FastAPI
from pydantic import BaseModel

from app.crud.user import UserCRUD

app = FastAPI()


class UserRegistration(BaseModel):
    name: str


@app.post("/register")
async def register(user: UserRegistration):
    token = await UserCRUD.register(user.name)
    return {"token": token}
