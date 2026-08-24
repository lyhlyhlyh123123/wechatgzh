import json

from pydantic import ValidationError

from app.schemas import BodyOut, CreatorOut
from app.services.prompt_store import read_prompt

MAX_ATTEMPTS = 3


def _ask(llm, system: str, user: str, schema):
    last_err: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        raw = llm.chat_json(system, user)
        try:
            return schema.model_validate(raw)
        except ValidationError as exc:
            last_err = exc
    raise ValueError(f"输出不符合约定结构: {last_err}")


def _package_valid(out: CreatorOut, bank_questions: set[str], used_questions: list[str]) -> bool:
    return (
        out.question in bank_questions
        and out.question not in used_questions
        and len(out.titles) == 3
    )


def create_package(llm, bank_text: str, used_questions: list[str]) -> CreatorOut:
    system = read_prompt("creator_system")
    bank_questions = {
        q for section in json.loads(bank_text).get("sections", [])
        for q in section.get("questions", [])
    }
    used_block = "\n".join(used_questions) if used_questions else "（暂无）"
    user = f"【题库】\n{bank_text}\n【已用问题（禁止选择）】\n{used_block}"
    out: CreatorOut = _ask(llm, system, user, CreatorOut)
    if not _package_valid(out, bank_questions, used_questions):
        rejected = out.question
        user = f"{user}\n【纠偏】问题“{rejected}”不在库中或已被占用，请另选未占用的问题并按原格式重新输出"
        out = _ask(llm, system, user, CreatorOut)
    if not _package_valid(out, bank_questions, used_questions):
        raise ValueError("创意包选题校验失败：问题不在库中或已被占用")
    return out


def gen_body(llm, conflict: str, title: str) -> BodyOut:
    system = read_prompt("body_system")
    user = json.dumps({"conflict": conflict, "title": title}, ensure_ascii=False)
    for _ in range(MAX_ATTEMPTS):
        out: BodyOut = _ask(llm, system, user, BodyOut)
        stripped = out.body.strip()
        clean_len = sum(1 for ch in stripped if "\u4e00" <= ch <= "\u9fff")
        if 15 <= clean_len <= 70:
            return BodyOut(body=stripped, mood=out.mood.strip())
    return out
