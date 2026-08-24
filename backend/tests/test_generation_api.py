import pytest

from app.schemas import BuildIn
from app.services.pipeline import build_article
from tests.test_pipeline import FakeArk, FakeLLM, make_llm

BUILD_BODY = {
    "topic_id": None,
    "conflict": "心动还是稳定",
    "title": "35岁，我选了稳定",
}


@pytest.fixture
def wired(client):
    llm = make_llm()
    ark = FakeArk()
    client.app.state.llm = llm
    client.app.state.ark = ark
    return client, llm, ark


def test_build_endpoint(wired):
    client, _, ark = wired
    r = client.post("/api/generation/build", json=BUILD_BODY)
    assert r.status_code == 200
    data = r.json()
    assert data["body"].startswith("以前总觉得")
    assert len(data["image_paths"]) == 1
    detail = client.get(f"/api/articles/{data['id']}")
    assert detail.status_code == 200


def test_regen_endpoints_only_touch_own_fields(wired):
    client, llm, ark = wired
    aid = client.post("/api/generation/build", json=BUILD_BODY).json()["id"]

    llm.responses.append({"candidates": [
        {"conflict": "新的冲突", "titles": ["新标题一", "新标题二", "新标题三", "新标题四", "新标题五"]},
    ]})
    r = client.post(f"/api/articles/{aid}/regen-titles")
    assert r.json()["title_candidates"][0]["titles"][0] == "新标题一"
    old_title = r.json()["title"]
    assert old_title == BUILD_BODY["title"]

    llm.responses.append({"body": "换一种说法的全新正文，字数刚好合适。", "mood": "深夜路灯"})
    r = client.post(f"/api/articles/{aid}/regen-body")
    data = r.json()
    assert data["body"].startswith("换一种说法")
    assert data["mood"] == "深夜路灯"

    r = client.post(f"/api/articles/{aid}/regen-images", json={"count": 2})
    assert len(r.json()["image_paths"]) == 2


def test_draft_conflicts_endpoint(wired):
    client, llm, _ = wired
    llm.responses.append({"candidates": [
        {"conflict": "c1", "titles": ["t1", "t2", "t3", "t4", "t5"]},
    ]})
    r = client.post("/api/generation/draft-conflicts", json={"idea": "大龄单身"})
    assert r.json()["candidates"][0]["conflict"] == "c1"


def test_build_and_regen_use_default_count(client, wired):
    client.app.state.default_count = 2
    art = client.post("/api/generation/build", json={
        "topic_id": None,
        "conflict": "c",
        "title": "默认数量标题",
    }).json()
    assert len(art["image_paths"]) == 2

    r = client.post(f"/api/articles/{art['id']}/regen-images")
    assert len(r.json()["image_paths"]) == 2
