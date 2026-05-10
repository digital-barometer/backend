import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

from db.database import async_session_maker
from db.enums import SourceType
from db.models import Source, Topic


load_dotenv(Path(__file__).resolve().parents[3] / ".env")
load_dotenv()


@dataclass(frozen=True, slots=True)
class SourceSeed:
    name: str
    source_type: SourceType
    base_url: str
    config: dict
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class TopicSeed:
    name: str
    slug: str
    keywords: list[str]
    is_active: bool = True


SOURCES = [
    SourceSeed(
        name="Google Trends",
        source_type=SourceType.SEARCH_TREND,
        base_url="https://trends.google.com",
        config={"connector": "pytrends_modern", "geo": "RU"},
    ),
    SourceSeed(
        name="Google News",
        source_type=SourceType.NEWS,
        base_url="https://news.google.com",
        config={
            "rss_url_template": (
                "https://news.google.com/rss/search?q={query}&hl=ru&gl=RU&ceid=RU:ru"
            )
        },
    ),
    SourceSeed(
        name="Habr",
        source_type=SourceType.FORUM,
        base_url="https://habr.com",
        config={
            "rss_url_template": "https://habr.com/ru/rss/search/?q={query}",
            "filter_locally": True,
        },
    ),
    SourceSeed(
        name="GDELT Project",
        source_type=SourceType.NEWS,
        base_url="https://www.gdeltproject.org",
        config={
            "connector": "gdelt_doc",
            "max_records": 100,
        },
    ),
    SourceSeed(
        name="NewsAPI",
        source_type=SourceType.NEWS,
        base_url="https://newsapi.org",
        config={
            "connector": "newsapi",
            "language": "ru",
            "page_size": 100,
            "sort_by": "publishedAt",
        },
        is_active=bool(os.getenv("NEWSAPI_API_KEY")),
    ),
]

TOPICS = [
    TopicSeed(
        name="OpenAI",
        slug="openai",
        keywords=["OpenAI", "ChatGPT"],
    ),
    TopicSeed(
        name="Python",
        slug="python",
        keywords=["Python"],
    ),
    TopicSeed(
        name="Искусственный интеллект",
        slug="iskusstvennyj-intellekt",
        keywords=["Искусственный интеллект", "ИИ", "AI"],
    ),
]


async def seed_data() -> None:
    async with async_session_maker() as session:
        source_count = await _upsert_sources(session)
        topic_count = await _upsert_topics(session)
        await session.commit()

    print(f"Seeded sources: {source_count}")
    print(f"Seeded topics: {topic_count}")


async def _upsert_sources(session) -> int:
    for item in SOURCES:
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

    return len(SOURCES)


async def _upsert_topics(session) -> int:
    for item in TOPICS:
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

    return len(TOPICS)


async def _get_source_by_name(session, name: str) -> Source | None:
    result = await session.execute(select(Source).where(Source.name == name).limit(1))
    return result.scalars().first()


async def _get_topic_by_slug(session, slug: str) -> Topic | None:
    result = await session.execute(select(Topic).where(Topic.slug == slug))
    return result.scalar_one_or_none()


if __name__ == "__main__":
    asyncio.run(seed_data())
