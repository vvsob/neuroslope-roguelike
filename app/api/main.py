from fastapi import FastAPI
from sqladmin import Admin, ModelView

from app.crud.user import UserCRUD
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.lobby import router as lobby_router

from app.db import engine, Base
from app.db.models import *

app = FastAPI()
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
