import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin, ModelView

from app.crud.user import UserCRUD
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.lobby import router as lobby_router
from app.api.endpoints.game import router as game_router

from app.db import engine, Base
from app.db.models import *

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_env() -> None:
    for env_file in (REPO_ROOT / ".env", REPO_ROOT / ".env.local"):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _parse_admin_ips(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {ip.strip() for ip in raw.split(",") if ip.strip()}


_load_env()
ADMIN_IPS = _parse_admin_ips(os.environ.get("ADMIN_IPS"))

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


@app.middleware("http")
async def admin_ip_guard(request: Request, call_next):
    if request.url.path.startswith("/admin"):
        if not ADMIN_IPS:
            return PlainTextResponse("Admin access is disabled", status_code=403)
        client_host = request.client.host if request.client else ""
        if client_host not in ADMIN_IPS:
            return PlainTextResponse(f"Forbidden", status_code=403)
    return await call_next(request)


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

# ── Frontend hosting (same port) ─────────────────────────────────────────────

INDEX_PATH = REPO_ROOT / "index.html"
SRC_DIR = REPO_ROOT / "src"

if SRC_DIR.exists():
    app.mount("/src", StaticFiles(directory=SRC_DIR), name="src")


@app.get("/", include_in_schema=False)
async def serve_index():
    if INDEX_PATH.exists():
        return FileResponse(INDEX_PATH)
    return {"error": "index.html not found"}
