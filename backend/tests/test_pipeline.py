from pathlib import Path

import pytest

from app.models import GenerationLog, Topic
from app.schemas import BuildIn, Candidate
from app.services.pipeline import build_article, draft_conflicts, source_text


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
        {"image_prompt": "candid photo of a woman at dusk"},
    ])


def test_source_text_from_topic(test_session, topic):
    text = source_text(test_session, topic_id=topic.id)
    assert "恐惧" in text and "遇不到合适的人" in text
    assert "自由想法" in source_text(test_session, idea="随便写写")


def test_draft_conflicts_logs(test_session, test_engine):
    from app.database import Base

    Base.metadata.create_all(test_engine)
    llm = FakeLLM([{"candidates": [
        {"conflict": "c", "titles": ["t1", "t2", "t3", "t4", "t5"]},
    ]}])
    out = draft_conflicts(test_session, llm, idea="x")
    assert len(out) == 1
    logs = test_session.query(GenerationLog).all()
    assert logs[0].stage == "conflict"
    assert logs[0].ok is True
    assert logs[0].model == "fake-model"


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
        candidates=[Candidate(conflict="心动还是稳定", titles=["35岁，我选了稳定"])],
    )
    article = build_article(
        test_session, llm, ark, data,
        storage_root=tmp_path / "storage",
        default_size="1080x1620", max_count=3,
    )
    assert article.body.startswith("以前总觉得")
    assert article.mood == "黄昏阳台"
    assert article.image_prompt == "candid photo of a woman at dusk"
    assert len(article.image_paths) == 2
    assert article.image_paths[0].startswith(f"runs/{article.id}/")
    saved = tmp_path / "storage" / article.image_paths[0]
    assert saved.read_bytes() == b"img"
    assert len(ark.calls) == 2
    assert ark.calls[0][1] == "1080x1620"
    stages = [l.stage for l in test_session.query(GenerationLog).all()]
    assert stages == ["body", "image_prompt", "image"]
    assert topic.use_count == 1
    assert article.title_candidates[0]["conflict"] == "心动还是稳定"


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
