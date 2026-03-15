from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqladmin import Admin, ModelView

from app.crud.user import UserCRUD
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.lobby import router as lobby_router
from app.api.endpoints.game import router as game_router

from app.db import engine, Base
from app.db.models import *

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4137",
        "http://127.0.0.1:4137",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?|http://\\[(::1|::)\\](:\\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
admin = Admin(app, engine)

# Проходимся по всем зарегистрированным моделям
for model_class in Base.__subclasses__():
    # Динамически создаем класс-наследник ModelView с помощью type()
    view_class = type(
        f"{model_class.__name__}Admin",
        (ModelView,),
        {
            "column_list": [column.name for column in model_class.__table__.columns],
            "column_details_list": [column.name for column in model_class.__table__.columns],
        },
        model=model_class  # <--- Передаем модель как kwarg для метакласса
    )

    admin.add_view(view_class)
app.include_router(auth_router)
app.include_router(lobby_router)
app.include_router(game_router)
