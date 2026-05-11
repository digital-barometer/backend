import asyncio
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SEED_DIR = Path(__file__).resolve().parent

from sqlalchemy import select

from db.database import async_session_maker
from db.enums import SourceType
from db.models import Source, Topic


@dataclass(frozen=True, slots=True)
class SourceSeed:
    name: str
    source_type: SourceType
    base_url: str
    config: dict[str, Any]
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class TopicSeed:
    name: str
    slug: str
    keywords: list[str]
    is_active: bool = True


async def seed_data() -> None:
    sources = _load_sources(SEED_DIR / "sources.csv")
    topics = _load_topics(SEED_DIR / "topics.csv")

    async with async_session_maker() as session:
        source_count = await _upsert_sources(session, sources)
        topic_count = await _upsert_topics(session, topics)
        await session.commit()

    print(f"Seeded sources: {source_count}")
    print(f"Seeded topics: {topic_count}")


def _load_sources(path: Path) -> list[SourceSeed]:
    rows = _read_csv(path)
    return [
        SourceSeed(
            name=row["name"],
            source_type=SourceType(row["source_type"]),
            base_url=row["base_url"],
            config=_load_json(row["config_json"], default={}),
            is_active=_is_active(row),
        )
        for row in rows
    ]


def _load_topics(path: Path) -> list[TopicSeed]:
    rows = _read_csv(path)
    return [
        TopicSeed(
            name=row["name"],
            slug=row["slug"],
            keywords=_load_json(row["keywords_json"], default=[]),
            is_active=_parse_bool(row.get("is_active"), default=True),
        )
        for row in rows
    ]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def _load_json(value: str | None, *, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def _is_active(row: dict[str, str]) -> bool:
    is_active = _parse_bool(row.get("is_active"), default=True)
    required_env = row.get("required_env")
    if required_env:
        return is_active and bool(os.getenv(required_env))
    return is_active


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


async def _upsert_sources(session, sources: list[SourceSeed]) -> int:
    for item in sources:
        source = await _get_source_by_name(session, item.name)
        if source is None:
            session.add(
                Source(
                    name=item.name,
                    source_type=item.source_type,
                    base_url=item.base_url,
                    config=item.config,
                    is_active=item.is_active,
                )
            )
            continue

        source.source_type = item.source_type
        source.base_url = item.base_url
        source.config = item.config
        source.is_active = item.is_active

    return len(sources)


async def _upsert_topics(session, topics: list[TopicSeed]) -> int:
    for item in topics:
        topic = await _get_topic_by_slug(session, item.slug)
        if topic is None:
            session.add(
                Topic(
                    name=item.name,
                    slug=item.slug,
                    keywords=item.keywords,
                    is_active=item.is_active,
                )
            )
            continue

        topic.name = item.name
        topic.keywords = item.keywords
        topic.is_active = item.is_active

    return len(topics)


async def _get_source_by_name(session, name: str) -> Source | None:
    result = await session.execute(select(Source).where(Source.name == name).limit(1))
    return result.scalars().first()


async def _get_topic_by_slug(session, slug: str) -> Topic | None:
    result = await session.execute(select(Topic).where(Topic.slug == slug))
    return result.scalar_one_or_none()


if __name__ == "__main__":
    asyncio.run(seed_data())
