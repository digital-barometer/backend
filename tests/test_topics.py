import unittest
from uuid import uuid4

from app.schemas.analysis import TopicCreateRequest, TopicUpdateRequest
from app.services.topics import TopicService


class FakeTopicRepository:
    def __init__(self) -> None:
        self.topics_by_slug = {}
        self.topics_by_id = {}
        self.added = []

    async def get_by_slug(self, slug):
        return self.topics_by_slug.get(slug)

    async def get_active_by_id(self, topic_id):
        topic = self.topics_by_id.get(topic_id)
        if topic and topic.is_active:
            return topic
        return None

    async def add(self, topic):
        topic.id = uuid4()
        self.topics_by_slug[topic.slug] = topic
        self.topics_by_id[topic.id] = topic
        self.added.append(topic)
        return topic


class TopicCreateRequestTest(unittest.TestCase):
    def test_create_request_normalizes_name_and_keywords(self) -> None:
        payload = TopicCreateRequest(
            name="  OpenAI   API ",
            keywords=[" ChatGPT ", "ChatGPT", "", " GPT-5 "],
        )

        self.assertEqual(payload.name, "OpenAI API")
        self.assertEqual(payload.keywords, ["ChatGPT", "GPT-5"])

    def test_update_request_normalizes_keywords(self) -> None:
        payload = TopicUpdateRequest(keywords=[" ChatGPT ", "ChatGPT", "", " GPT-5 "])

        self.assertEqual(payload.keywords, ["ChatGPT", "GPT-5"])


class TopicServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_topic_uses_explicit_keywords_only(self) -> None:
        repository = FakeTopicRepository()
        service = TopicService(repository)

        topic = await service.create("OpenAI", ["ChatGPT"])

        self.assertEqual(topic.name, "OpenAI")
        self.assertEqual(topic.slug, "openai")
        self.assertEqual(topic.keywords, ["ChatGPT"])
        self.assertTrue(topic.is_active)
        self.assertEqual(repository.added, [topic])

    async def test_create_existing_topic_rejects_duplicate_slug(self) -> None:
        repository = FakeTopicRepository()
        service = TopicService(repository)

        await service.create("OpenAI", ["ChatGPT"])

        with self.assertRaises(ValueError):
            await service.create(" OpenAI ", ["GPT-5"])

    async def test_update_keywords_changes_existing_topic(self) -> None:
        repository = FakeTopicRepository()
        service = TopicService(repository)

        topic = await service.create("OpenAI", ["ChatGPT"])
        updated = await service.update_keywords(topic.id, [" GPT-5 ", "GPT-5"])

        self.assertIs(updated, topic)
        self.assertEqual(updated.keywords, ["GPT-5"])

    async def test_update_keywords_rejects_unknown_topic(self) -> None:
        service = TopicService(FakeTopicRepository())

        with self.assertRaises(LookupError):
            await service.update_keywords(uuid4(), ["GPT-5"])


if __name__ == "__main__":
    unittest.main()
