import pytest

from app.schemas import CreatorOut
from app.services.stages import create_package, gen_body


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat_json(self, system, user, temperature=0.8):
        self.calls.append((system, user, temperature))
        return self.responses.pop(0)


BANK = "【自我认知】35岁还没活成自己想要的样子，是我错了吗\n【婚姻】心动和稳定，只能选一个吗"
Q_USED = "【自我认知】35岁还没活成自己想要的样子，是我错了吗"
Q_FREE = "【婚姻】心动和稳定，只能选一个吗"


def pkg(question):
    return {
        "question": question,
        "conflict": "她以为退让能换来平静，却发现对方得寸进尺",
        "titles": ["38岁那年我选择了退让", "退了三年我才看清楚", "这段关系里谁在装睡"],
        "body": "以前总觉得忍一忍就过去了，后来才发现，让步换不来尊重。",
        "mood": "黄昏阳台",
        "image_prompt": "candid phone photo of a woman on a balcony at dusk",
    }


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


def test_create_package_ok():
    llm = FakeLLM([pkg(Q_FREE)])
    out = create_package(llm, BANK, [])
    assert isinstance(out, CreatorOut)
    assert out.question == Q_FREE
    assert len(out.titles) == 3
    assert len(llm.calls) == 1
    user_msg = llm.calls[0][1]
    assert "35岁还没活成自己想要的样子" in user_msg
    assert "【已用问题（禁止选择）】" in user_msg
    assert "（暂无）" in user_msg


def test_create_package_corrects_occupied_question():
    llm = FakeLLM([pkg(Q_USED), pkg(Q_FREE)])
    out = create_package(llm, BANK, [Q_USED])
    assert out.question == Q_FREE
    assert len(llm.calls) == 2
    second = llm.calls[1][1]
    assert "纠偏" in second
    assert Q_USED in second


def test_create_package_raises_when_still_occupied():
    llm = FakeLLM([pkg(Q_USED), pkg(Q_USED)])
    with pytest.raises(ValueError, match="创意包选题校验失败"):
        create_package(llm, BANK, [Q_USED])
    assert len(llm.calls) == 2


def test_create_package_retries_when_titles_not_three():
    bad = pkg(Q_FREE)
    bad["titles"] = bad["titles"][:2]
    llm = FakeLLM([bad, pkg(Q_FREE)])
    out = create_package(llm, BANK, [])
    assert len(out.titles) == 3
    assert len(llm.calls) == 2
