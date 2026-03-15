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

