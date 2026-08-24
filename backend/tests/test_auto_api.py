import pytest
from sqlalchemy.orm import sessionmaker

from tests.test_pipeline import FakeArk, FakeLLM


def bank_llm(n):
    responses = []
    for _ in range(n):
        responses += [
            {"candidates": [{"conflict": "自动冲突", "titles": ["自动标题一", "t2", "t3", "t4", "t5"]}]},
            {"body": "全自动生成的正文内容大概三十个字左右了", "mood": "清晨厨房"},
            {"image_prompt": "auto candid photo"},
        ]
    return FakeLLM(responses)


def test_auto_creates_distinct_articles(client):
    client.app.state.llm = bank_llm(2)
    client.app.state.ark = FakeArk()
    r = client.post("/api/generation/auto?count=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["articles"]) == 2
    assert len({a["topic_id"] for a in body["articles"]}) == 2
    assert all(a["title"] == "自动标题一" for a in body["articles"])


def test_auto_exhaustion(test_engine, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import seed as seed_mod
    from app.database import Base
    from app.main import create_app
    from app.models import Topic
    from app.services.pipeline import auto_generate

    monkeypatch.setattr(seed_mod, "SEED_TOPICS", [])
    monkeypatch.setattr(seed_mod, "BANK_PATH", tmp_path / "missing_bank.json")
    Base.metadata.create_all(test_engine)
    Session = sessionmaker(bind=test_engine, autoflush=False)
    create_app(
        session_factory=Session,
        db_engine=test_engine,
        storage_root=str(tmp_path / "storage"),
    )

    db = Session()
    db.add(Topic(drive_type="欲望", category="x", conflict="唯一的问题"))
    db.commit()

    def make_llm():
        return FakeLLM([
            {"candidates": [{"conflict": "c", "titles": ["t1", "t2", "t3", "t4", "t5"]}]},
            {"body": "正文内容字数大概在合适范围之内了", "mood": "m"},
            {"image_prompt": "p"},
        ])

    art = auto_generate(db, make_llm(), FakeArk(), tmp_path / "storage", "1080x1620", 3)
    assert art.topic_id is not None
    with pytest.raises(ValueError, match="已全部使用"):
        auto_generate(db, make_llm(), FakeArk(), tmp_path / "storage", "1080x1620", 3)
    db.close()
