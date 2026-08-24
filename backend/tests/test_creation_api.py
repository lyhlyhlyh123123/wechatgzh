import json
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from app.models import Article
from tests.test_pipeline import FakeArk, FakeLLM


def bank_question():
    bank = json.loads(
        Path("templates/prompts/question_bank.json").read_text(encoding="utf-8")
    )
    return bank["sections"][0]["questions"][0]


def package(question):
    return {
        "question": question,
        "conflict": "她以为退让能换来平静，却发现对方得寸进尺",
        "titles": ["38岁那年我选择了退让", "退了三年我才看清楚", "这段关系里谁在装睡"],
        "body": "以前总觉得忍一忍就过去了，后来才发现，让步换不来尊重。",
        "mood": "黄昏阳台",
        "image_prompt": "candid phone photo of a woman on a balcony at dusk",
    }


def test_one_shot_creates_article(client, test_engine):
    question = bank_question()
    client.app.state.llm = FakeLLM([
        package(question),
        {"body": "全自动正文三十字上下刚好合适的长度呀", "mood": "清晨厨房"},
    ])
    client.app.state.ark = FakeArk()
    r = client.post("/api/creation/one-shot")
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "38岁那年我选择了退让"
    assert data["status"] == "draft"
    assert data["image_prompt"] == "candid phone photo of a woman on a balcony at dusk"
    assert len(data["image_paths"]) == 1
    assert [c["conflict"] for c in data["title_candidates"]] == [
        "她以为退让能换来平静，却发现对方得寸进尺"
    ]

    Session = sessionmaker(bind=test_engine, autoflush=False)
    db = Session()
    art = db.get(Article, data["id"])
    assert art.question_text == question
    db.close()


def test_one_shot_exhaustion_returns_400(client, test_engine, monkeypatch):
    from app import seed as seed_mod

    monkeypatch.setattr(seed_mod, "SEED_TOPICS", [])
    question = bank_question()
    Session = sessionmaker(bind=test_engine, autoflush=False)
    db = Session()
    db.add(Article(title="占位文章", question_text=question))
    db.commit()
    db.close()

    client.app.state.llm = FakeLLM([package(question), package(question)])
    r = client.post("/api/creation/one-shot")
    assert r.status_code == 400
    assert "已被占用" in r.json()["detail"]
