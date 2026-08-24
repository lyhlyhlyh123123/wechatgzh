from pathlib import Path

import pytest

from app.models import GenerationLog, Topic
from app.schemas import BuildIn, Candidate
from app.services.pipeline import build_article


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.model = "fake-model"

    def chat_json(self, system, user, temperature=0.8):
        self.calls.append((system, user))
        return self.responses.pop(0)


class FakeArk:
    def __init__(self):
        self.calls = []

    def generate_image(self, prompt, size, output_path):
        self.calls.append((prompt, size))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"img")
        return output_path


@pytest.fixture
def topic(test_session):
    t = Topic(drive_type="恐惧", category="情感关系", conflict="遇不到合适的人")
    test_session.add(t)
    test_session.commit()
    return t


def make_llm():
    return FakeLLM([
        {"body": "以前总觉得来日方长，现在只想过好今天。", "mood": "黄昏阳台"},
    ])


def test_build_article_full_flow(test_session, test_engine, tmp_path, topic):
    from app.database import Base

    Base.metadata.create_all(test_engine)
    llm = make_llm()
    ark = FakeArk()
    data = BuildIn(
        topic_id=topic.id,
        conflict="心动还是稳定",
        title="35岁，我选了稳定",
        image_count=2,
        image_prompt="candid photo of a woman at dusk",
        question_text="35岁还没活成自己想要的样子，是我错了吗",
        candidates=[Candidate(conflict="心动还是稳定", titles=["35岁，我选了稳定"])],
    )
    article = build_article(
        test_session, llm, ark, data,
        storage_root=tmp_path / "storage",
        default_size="1080x1620", max_count=3,
    )
    assert article.body.startswith("以前总觉得")
    assert article.mood == "黄昏阳台"
    assert len(article.image_paths) == 2
    assert article.image_paths[0].startswith(f"runs/{article.id}/")
    saved = tmp_path / "storage" / article.image_paths[0]
    assert saved.read_bytes() == b"img"
    assert len(ark.calls) == 2
    assert ark.calls[0] == ("candid photo of a woman at dusk", "1080x1620")
    stages = [l.stage for l in test_session.query(GenerationLog).all()]
    assert stages == ["body", "image"]
    assert topic.use_count == 1
    assert article.title_candidates[0]["conflict"] == "心动还是稳定"


def test_build_article_consumes_buildin_fields(test_session, test_engine, tmp_path):
    from app.database import Base

    Base.metadata.create_all(test_engine)
    data = BuildIn(
        conflict="心动还是稳定",
        title="35岁，我选了稳定",
        image_count=1,
        image_prompt="直通的人像提示词",
        question_text="心动和稳定，只能选一个吗",
    )
    article = build_article(
        test_session, make_llm(), FakeArk(), data,
        storage_root=tmp_path / "storage",
        default_size="1080x1620", max_count=3,
    )
    assert article.image_prompt == "直通的人像提示词"
    assert article.question_text == "心动和稳定，只能选一个吗"
    assert [l.stage for l in test_session.query(GenerationLog).all()] == ["body", "image"]


def test_build_respects_max_count(test_session, test_engine, tmp_path, topic):
    from app.database import Base

    Base.metadata.create_all(test_engine)
    ark = FakeArk()
    data = BuildIn(topic_id=topic.id, conflict="c", title="t", image_count=9)
    article = build_article(
        test_session, make_llm(), ark, data,
        storage_root=tmp_path / "storage",
        default_size="1080x1620", max_count=3,
    )
    assert len(article.image_paths) == 3
