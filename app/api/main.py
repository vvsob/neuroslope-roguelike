from fastapi import FastAPI
from app.crud.user import UserCRUD
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.lobby import router as lobby_router

app = FastAPI()
app.include_router(auth_router)
app.include_router(lobby_router)
