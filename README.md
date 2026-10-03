<div align="center">

![Digital Barometer](docs/assets/logo.svg){width=96 height=96}

# Digital Barometer · backend

**API, сбор данных и LLM-анализ тональности для сервиса «Цифровой барометр».**

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=flat-square&logo=langchain&logoColor=white)
![uv](https://img.shields.io/badge/uv-DE5FE9?style=flat-square&logo=uv&logoColor=white)

</div>

---

Сервис собирает упоминания темы из нескольких источников, оценивает их
тональность и эмоции с помощью LLM и сводит результаты в тренды и графики.

Это один из трёх репозиториев системы — общий обзор в
[профиле группы](https://gitlab.com/digital-barometer):

| | Репозиторий | Назначение |
| :---: | --- | --- |
| 🧠 | **backend** (этот) | REST API, сбор данных, LLM-анализ |
| 📊 | [**frontend**](https://gitlab.com/digital-barometer/frontend) | Веб-интерфейс: темы, источники, графики |
| 🛠️ | [**infra**](https://gitlab.com/digital-barometer/infra) | Traefik и PostgreSQL |

## Архитектура

![Архитектура](docs/assets/architecture.png)

Слои: `api → services → repositories → db`.

| Каталог | Что внутри |
| --- | --- |
| `app/api` | HTTP-роуты: `topics`, `sources`, `analysis`, `health` |
| `app/services` | Бизнес-логика: `analysis`, `sentiment`, `summary`, `search_plan`, `source_fetch`, `metrics`, `topics`, `sources` |
| `app/repositories` | Доступ к данным: `topics`, `sources`, `analysis` |
| `app/connectors` | Адаптеры источников, выбираются через `ConnectorFactory` по типу источника |
| `app/core` | Настройки (`pydantic-settings`) и DI-контейнер (`dishka`) |
| `src/db` | Отдельный пакет `digital-barometer-db`: модели SQLAlchemy и миграции Alembic, подключён как editable-зависимость |

## Как проходит анализ

![Схема анализа](docs/assets/flowchart.png)

Источники опрашиваются параллельно, результаты приводятся к общей модели
(`Mention` / `TrendPoint` / `SourceResult`) и дедуплицируются по SHA-256
хешу содержимого. Если LLM недоступна, тональность и эмоции оцениваются
эвристикой на регулярках, и запуск не падает. Каждый источник
отслеживается отдельно, поэтому запуск завершается со статусом `success`,
`partial` или `failed`.

## Источники данных

| Коннектор | Источник |
| --- | --- |
| `gdelt_doc` | GDELT Doc API |
| `newsapi` | NewsAPI |
| RSS | произвольные RSS-ленты |
| Google Trends | через SerpApi |

Все запросы к источникам проходят через общий лимит
`SOURCE_FETCH_MAX_CONCURRENCY` и, при необходимости, через прокси
`OUTBOUND_PROXY_URL`. API-ключи и заголовки `Authorization` вычищаются из
текста ошибок перед логированием
(`app/services/source_fetch.py:redact_sensitive_text`).

## API

| Метод | Путь | Описание |
| --- | --- | --- |
| `GET` | `/health` | Проверка состояния |
| `GET` | `/sources` | Список доступных источников |
| `GET` | `/topics` | Список тем |
| `POST` | `/topics` | Создать тему |
| `PATCH` | `/topics/{id}` | Изменить тему |
| `POST` | `/analysis` | Запустить анализ |
| `GET` | `/analysis/{id}` | Результат анализа |
| `GET` | `/analysis/{id}/charts` | Данные для графиков |

Swagger UI доступен по адресу `/docs`.

## База данных

<details>
<summary>ER-диаграмма и описание таблиц</summary>

![ER-диаграмма](docs/assets/db.png)

| Таблица | Назначение |
| --- | --- |
| `topics` | Отслеживаемые темы и их ключевые слова |
| `sources` | Настроенные источники данных для темы |
| `analysis_runs` | Один запуск анализа темы за период |
| `source_results` | Результат опроса источника в рамках запуска |
| `mentions` | Собранные упоминания с оценками тональности и эмоций |
| `trend_points` | Временные ряды по источникам (например, Google Trends) |
| `analysis_metrics` | Агрегированные показатели и итоговый индекс «барометра» |
| `reports` | Сгенерированные файлы отчётов по запуску |

</details>

## Локальный запуск

```bash
cp .env.example .env
uv sync
uv run alembic -c src/db/alembic.ini upgrade head
uv run uvicorn app.main:app --reload --app-dir src --port 8000
```

API будет доступен на `http://localhost:8000`.

Через Docker:

```bash
cp .env.example .env
docker compose up --build
```

### Переменные окружения

| Группа | Переменные |
| --- | --- |
| PostgreSQL | `POSTGRES_*` |
| LLM | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LANGCHAIN_MODEL`, `SENTIMENT_MODEL`, `ANALYSIS_MODEL`, `LLM_*` |
| Источники | `NEWSAPI_API_KEY`, `SERPAPI_API_KEY` |
| Сеть | `OUTBOUND_PROXY_URL`, `REQUEST_TIMEOUT_SECONDS`, `CORS_ALLOW_ORIGINS` |

Полный список — в `.env.example`.

## Тесты

```bash
uv run python -m unittest discover -s tests
```

Покрыты: фабрика коннекторов, коннектор GDELT, метрики и вычистка секретов
при ошибках источников, построение плана поиска, работа с темами.

## CI/CD

Пайплайн в `.gitlab-ci.yml`:

1. **`test_backend`** — `uv sync --frozen` и `unittest discover` на чистом PostgreSQL.
2. **`build_image`** — собирает и пушит три образа: API, миграции
   (`Dockerfile.migrate`) и наполнение данными (`Dockerfile.seed`).
   Только для веток `main` и `stage`.
3. **`deploy_stage` / `deploy_prod`** — по SSH на целевой хост:
   `docker compose pull`, миграции, наполнение, выкатка `api`.

<details>
<summary>Переменные CI</summary>

| Окружение | Переменные |
| --- | --- |
| staging | `SSH_PRIVATE_KEY_STAGE`, `SSH_HOST_STAGE`, `SSH_PORT_STAGE`, `SSH_USER_STAGE`, `STAGE_ENV_FILE` |
| production | `SSH_PRIVATE_KEY`, `SSH_HOST_PROD`, `SSH_PORT_PROD`, `SSH_USER_PROD`, `PROD_ENV_FILE` |
| общие | `BASE_DEPLOY_PATH` |

</details>
