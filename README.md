# Digital Barometer — backend

API сервиса «Цифровой барометр» — анализ медиа-упоминаний по теме: сбор данных
из нескольких источников, LLM-разметка тональности и эмоций, агрегация в
тренды и графики.

Стек: **FastAPI + dishka (DI) + PostgreSQL + LangChain (OpenAI-совместимый LLM)**.

## Архитектура

Слоистая структура: `api → services → repositories → db`.

- `app/api` — HTTP-роуты (`topics`, `sources`, `analysis`, `health`)
- `app/services` — бизнес-логика: `analysis`, `sentiment`, `summary`,
  `search_plan`, `source_fetch`, `metrics`, `topics`, `sources`
- `app/repositories` — доступ к данным (`topics`, `sources`, `analysis`)
- `app/connectors` — адаптеры источников данных, выбираются через
  `ConnectorFactory` по типу источника
- `app/core` — настройки (`pydantic-settings`) и DI-контейнер (`dishka`)
- `src/db` — отдельный пакет (`digital-barometer-db`), модели SQLAlchemy,
  Alembic-миграции, подключается как editable-зависимость

## Источники данных

| Коннектор | Источник |
| --- | --- |
| `gdelt_doc` | GDELT Doc API |
| `newsapi` | NewsAPI |
| RSS | произвольные RSS-ленты |
| Google Trends | через SerpApi |

Все запросы к источникам идут через общий `SOURCE_FETCH_MAX_CONCURRENCY` и
опциональный `OUTBOUND_PROXY_URL`. Чувствительные данные (API-ключи,
`Authorization`) вычищаются из текста ошибок перед логированием
(`app/services/source_fetch.py:redact_sensitive_text`).

## Эндпоинты

`GET /health`,
`GET /sources`,
`POST /topics`, `PATCH /topics/{id}`, `GET /topics`,
`POST /analysis`, `GET /analysis/{id}`, `GET /analysis/{id}/charts`.

## Локальный запуск

```bash
cp .env.example .env
uv sync
uv run alembic -c src/db/alembic.ini upgrade head
uv run uvicorn app.main:app --reload --app-dir src --port 8000
```

API доступен на `http://localhost:8000`, Swagger — `/docs`.

Через Docker:

```bash
cp .env.example .env
docker compose up --build
```

Переменные окружения (`.env.example`): подключение к PostgreSQL
(`POSTGRES_*`), LLM (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LANGCHAIN_MODEL`,
`SENTIMENT_MODEL`, `ANALYSIS_MODEL`, `LLM_*`), источники (`NEWSAPI_API_KEY`,
`SERPAPI_API_KEY`), сеть (`OUTBOUND_PROXY_URL`, `REQUEST_TIMEOUT_SECONDS`,
`CORS_ALLOW_ORIGINS`).

## Тесты

```bash
uv run python -m unittest discover -s tests
```

Покрыты: фабрика коннекторов, GDELT-коннектор, метрики и редактирование
секретов при фейле источника, построение поискового плана, работа с топиками.

## CI/CD (GitLab)

`.gitlab-ci.yml`:

1. `test_backend` — `uv sync --frozen` + `unittest discover` на чистой
   PostgreSQL.
2. `build_image` — сборка и push трёх образов: API, миграции (`Dockerfile.migrate`),
   сид данных (`Dockerfile.seed`) (только `main`, `stage`).
3. `deploy_stage` / `deploy_prod` — SSH на целевой хост, `docker compose pull`,
   прогон миграций и сидирования, накат `api`.

Требуемые CI-переменные: `SSH_PRIVATE_KEY_STAGE`/`SSH_PRIVATE_KEY`,
`SSH_HOST_STAGE`/`SSH_HOST_PROD`, `SSH_PORT_STAGE`/`SSH_PORT_PROD`,
`SSH_USER_STAGE`/`SSH_USER_PROD`, `STAGE_ENV_FILE`/`PROD_ENV_FILE`,
`BASE_DEPLOY_PATH`.
