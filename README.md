# Digital Barometer — backend

API for the "Digital Barometer" service — media-mention analysis for a topic:
collecting data from multiple sources, LLM-based sentiment/emotion scoring,
and aggregating results into trends and charts.

Stack: **FastAPI + dishka (DI) + PostgreSQL + LangChain (OpenAI-compatible LLM)**.

This repo is one of three that make up the system:

| Repository | Stack | Role |
| --- | --- | --- |
| **backend** (this repo) | FastAPI, dishka (DI), PostgreSQL, LangChain | REST API, data collection, LLM analysis |
| [**frontend**](https://github.com/digital-barometer/frontend) | React 18, TypeScript, Vite, Tailwind CSS, Recharts | Web UI: topics, sources, analysis charts |
| [**infra**](https://github.com/digital-barometer/infra) | Traefik, PostgreSQL, Docker Compose | Reverse proxy (TLS via Let's Encrypt) and database |

## Architecture

![Architecture](docs/assets/architecture.png)

Layered structure: `api → services → repositories → db`.

- `app/api` — HTTP routes (`topics`, `sources`, `analysis`, `health`)
- `app/services` — business logic: `analysis`, `sentiment`, `summary`,
  `search_plan`, `source_fetch`, `metrics`, `topics`, `sources`
- `app/repositories` — data access (`topics`, `sources`, `analysis`)
- `app/connectors` — data source adapters, selected via
  `ConnectorFactory` based on source type
- `app/core` — settings (`pydantic-settings`) and DI container (`dishka`)
- `src/db` — a separate package (`digital-barometer-db`) with SQLAlchemy
  models and Alembic migrations, included as an editable dependency

## Tech Stack

**Core:** FastAPI, dishka (DI), Pydantic Settings

**Data sources:** GDELT Doc API, NewsAPI, RSS feeds, Google Trends (via SerpApi) —
see [Data sources](#data-sources) below for details

**AI:** LangChain, OpenAI-compatible LLM endpoint — batched sentiment and
emotion scoring, topic summaries; falls back to a regex-based heuristic when
the LLM is unavailable

**Database:** PostgreSQL + SQLAlchemy (async) + Alembic

**Infrastructure:** Docker Compose, Traefik (automatic TLS), GitLab CI
(`test → build → deploy`, staging + production)

## Database Schema

![ERD](docs/assets/db.png)

| Table | Purpose |
| --- | --- |
| `topics` | Monitored topics and their keywords |
| `sources` | Configured data sources (GDELT, NewsAPI, RSS, Trends) per topic |
| `analysis_runs` | A single analysis execution for a topic over a date range |
| `source_results` | Per-source fetch outcome within a run (status, raw payload, item counts) |
| `mentions` | Individual mentions collected from sources, with sentiment/emotion scores |
| `trend_points` | Time-series metrics per source (e.g. Google Trends values) |
| `analysis_metrics` | Aggregated sentiment/emotion counts and the resulting "barometer" score |
| `reports` | Generated report files per analysis run |

## Analysis Flow

![Analysis flow](docs/assets/flowchart.png)

Sources are fetched concurrently and normalized into a common model
(`Mention` / `TrendPoint` / `SourceResult`), deduplicated by a SHA-256
content hash. If the LLM is unavailable, sentiment/emotion scoring falls
back to a regex-based heuristic instead of failing the run. Each source
result is tracked independently, so a run can finish as `success`,
`partial`, or `failed` depending on which sources succeeded.

## Data sources

| Connector | Source |
| --- | --- |
| `gdelt_doc` | GDELT Doc API |
| `newsapi` | NewsAPI |
| RSS | arbitrary RSS feeds |
| Google Trends | via SerpApi |

All requests to sources go through a shared `SOURCE_FETCH_MAX_CONCURRENCY`
limit and an optional `OUTBOUND_PROXY_URL`. Sensitive data (API keys,
`Authorization` headers) is stripped from error text before logging
(`app/services/source_fetch.py:redact_sensitive_text`).

## Endpoints

`GET /health`,
`GET /sources`,
`POST /topics`, `PATCH /topics/{id}`, `GET /topics`,
`POST /analysis`, `GET /analysis/{id}`, `GET /analysis/{id}/charts`.

## Running locally

```bash
cp .env.example .env
uv sync
uv run alembic -c src/db/alembic.ini upgrade head
uv run uvicorn app.main:app --reload --app-dir src --port 8000
```

The API is available at `http://localhost:8000`, Swagger UI at `/docs`.

Via Docker:

```bash
cp .env.example .env
docker compose up --build
```

Environment variables (`.env.example`): PostgreSQL connection
(`POSTGRES_*`), LLM (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LANGCHAIN_MODEL`,
`SENTIMENT_MODEL`, `ANALYSIS_MODEL`, `LLM_*`), data sources (`NEWSAPI_API_KEY`,
`SERPAPI_API_KEY`), networking (`OUTBOUND_PROXY_URL`, `REQUEST_TIMEOUT_SECONDS`,
`CORS_ALLOW_ORIGINS`).

## Tests

```bash
uv run python -m unittest discover -s tests
```

Covered: connector factory, GDELT connector, metrics and secret redaction
on source failure, search-plan construction, topic handling.

## CI/CD (GitLab)

`.gitlab-ci.yml`:

1. `test_backend` — `uv sync --frozen` + `unittest discover` against a
   clean PostgreSQL instance.
2. `build_image` — builds and pushes three images: API, migrations
   (`Dockerfile.migrate`), data seeding (`Dockerfile.seed`) (`main`, `stage`
   branches only).
3. `deploy_stage` / `deploy_prod` — SSH into the target host,
   `docker compose pull`, run migrations and seeding, roll out `api`.

Required CI variables: `SSH_PRIVATE_KEY_STAGE`/`SSH_PRIVATE_KEY`,
`SSH_HOST_STAGE`/`SSH_HOST_PROD`, `SSH_PORT_STAGE`/`SSH_PORT_PROD`,
`SSH_USER_STAGE`/`SSH_USER_PROD`, `STAGE_ENV_FILE`/`PROD_ENV_FILE`,
`BASE_DEPLOY_PATH`.
