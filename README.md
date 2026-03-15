# Neuroslope Spire Prototype

A lightweight Slay the Spire style prototype built with plain JavaScript and browser UI.

## Features

- Branching run map with hallway fights, elites, campfires, treasure, and a boss
- Card combat with energy, draw pile, discard pile, exhaust-style turn flow, and enemy intents
- Persistent run state across battles
- Post-combat card rewards and campfire healing
- Per-floor enemy and weapon art slots with a batch image generation script
- No build step required

## Run it

Because browsers block ES modules from `file://` URLs, serve the project with a tiny local web server from the repo root.

```bash
python3 -m http.server 4173
```

Then open `http://localhost:4173`.

## Generate level art

The game looks for generated images in `src/assets/generated/`. Use the Python script to create enemy and weapon art for all combat themes:

```bash
HF_TOKEN=your_token_here python3 src/gen_image.py
```

Generate only one asset family or one floor if needed:

```bash
HF_TOKEN=your_token_here python3 src/gen_image.py --kind weapon
HF_TOKEN=your_token_here python3 src/gen_image.py --level n5 --kind enemy
```

If a generated image is missing, the UI falls back to the placeholder SVGs.

## How to play

- Click a map node to travel
- Play cards from your hand during combat
- Click `End Turn` to let the enemy act
- After combat, choose one reward card to add it to your deck
- Reach the final boss and survive

# neuroslope-roguelike

Минимальный backend-сервис на **FastAPI + SQLAlchemy + Alembic**.

## Что в проекте

- API: `app/api/main.py`
- Точка входа ASGI: `app.api.main:app`
- Миграции: `alembic/`
- База данных: SQLite (`database.sqlite` в корне проекта)

## Требования

- Python **3.12+**
- [Poetry](https://python-poetry.org/docs/#installation)

## Установка

Из корня проекта:

```zsh
poetry install
```

## Миграции БД

Применить все миграции:

```zsh
poetry run alembic upgrade head
```

Создать новую миграцию (если меняли модели):

```zsh
poetry run alembic revision --autogenerate -m "описание_изменений"
poetry run alembic upgrade head
```

## Запуск сервера

```zsh
poetry run uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

После запуска:

- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## Быстрая проверка API

### Регистрация пользователя

```zsh
curl -X POST 'http://127.0.0.1:8000/register' \
  -H 'Content-Type: application/json' \
  -d '{"name":"test_user"}'
```

Ожидается JSON с токеном:

```json
{"token":"..."}
```

## Частые проблемы

### 1) `ModuleNotFoundError: No module named 'app'`
Запускайте команды из **корня проекта** и через `poetry run`.

### 2) Alembic работает не с той SQLite
В `alembic.ini` уже задан путь через `%(here)s`, поэтому миграции должны идти в `database.sqlite` в корне.

### 3) Порт 8000 занят
Запустите на другом порту:

```zsh
poetry run uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8001
```
