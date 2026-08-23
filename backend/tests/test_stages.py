import pytest

from app.schemas import Candidate
from app.services.stages import draft_conflicts, gen_body, gen_image_prompt


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat_json(self, system, user, temperature=0.8):
        self.calls.append((system, user, temperature))
        return self.responses.pop(0)


def test_draft_conflicts_ok():
    llm = FakeLLM([{
        "candidates": [
            {"conflict": "c1", "titles": ["t1", "t2", "t3", "t4", "t5"]},
            {"conflict": "c2", "titles": ["a", "b", "c", "d", "e"]},
        ]
    }])
    out = draft_conflicts(llm, "主题：恐惧\n素材：遇不到合适的人")
    assert isinstance(out[0], Candidate)
    assert len(out) == 2
    assert "遇不到合适的人" in llm.calls[0][1]


def test_draft_conflicts_retries_on_bad_shape():
    llm = FakeLLM([
        {"wrong": 1},
        {"candidates": [{"conflict": "c", "titles": ["t1", "t2", "t3", "t4", "t5"]}]},
    ])
    out = draft_conflicts(llm, "x")
    assert len(llm.calls) == 2


def test_gen_body():
    llm = FakeLLM([{"body": "以前总觉得来日方长。" * 2, "mood": "黄昏阳台"}])
    out = gen_body(llm, "冲突", "标题")
    assert len(out.body) >= 10
    assert out.mood == "黄昏阳台"


def test_gen_body_enforces_length_after_retry():
    long_body = "字" * 80
    llm = FakeLLM([
        {"body": long_body, "mood": "m"},
        {"body": "三十字左右的正常正文内容大概就是这样了", "mood": "m"},
    ])
    out = gen_body(llm, "c", "t")
    assert len(out.body) <= 60


def test_gen_image_prompt_formats_template(monkeypatch):
    from app.services import stages

    monkeypatch.setattr(
        stages, "read_prompt",
        lambda name: "MOOD={mood} BODY={body}",
    )
    llm = FakeLLM([{"image_prompt": "photo of a woman"}])
    prompt = gen_image_prompt(llm, "正文内容", "雨夜车内")
    assert prompt == "photo of a woman"
    user_msg = llm.calls[0][1]
    assert "雨夜车内" in user_msg and "正文内容" in user_msg
