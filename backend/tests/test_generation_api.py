import pytest
from sqlalchemy.orm import sessionmaker

from app.schemas import ArticleOut, BuildIn
from app.services.pipeline import build_article
from tests.test_pipeline import FakeArk, FakeLLM

BODY_RESP = {"body": "以前总觉得来日方长，现在只想过好今天。", "mood": "黄昏阳台"}

BUILD_BODY = {
    "topic_id": None,
    "conflict": "心动还是稳定",
    "title": "35岁，我选了稳定",
    "image_prompt": "test prompt",
    "question_text": "测试问题",
}


@pytest.fixture
def wired(client):
    llm = FakeLLM([])
    ark = FakeArk()
    client.app.state.llm = llm
    client.app.state.ark = ark
    return client, llm, ark


def make_article(client, test_engine, **overrides):
    Session = sessionmaker(bind=test_engine, autoflush=False)
    db = Session()
    data = BuildIn(**{**BUILD_BODY, **overrides}, image_count=1)
    article = build_article(
        db, FakeLLM([dict(BODY_RESP)]), FakeArk(), data,
        storage_root=client.storage_root,
    )
    out = ArticleOut.model_validate(article).model_dump()
    db.close()
    return out


def test_regen_endpoints_only_touch_own_fields(client, test_engine, wired):
    client, llm, _ = wired
    aid = make_article(client, test_engine)["id"]

    llm.responses.append({"body": "换一种说法的全新正文，字数刚好合适。", "mood": "深夜路灯"})
    r = client.post(f"/api/articles/{aid}/regen-body")
    data = r.json()
    assert data["body"].startswith("换一种说法")
    assert data["mood"] == "深夜路灯"
    assert data["title"] == BUILD_BODY["title"]
    assert data["image_prompt"] == BUILD_BODY["image_prompt"]

    r = client.post(f"/api/articles/{aid}/regen-images", json={"count": 2})
    assert len(r.json()["image_paths"]) == 2
    assert r.json()["body"].startswith("换一种说法")


def test_regen_images_use_default_count(client, test_engine, wired):
    client.app.state.default_count = 2
    aid = make_article(client, test_engine)["id"]
    r = client.post(f"/api/articles/{aid}/regen-images")
    assert len(r.json()["image_paths"]) == 2
