import json

from pydantic import ValidationError

from app.schemas import BodyOut, ConflictsOut, ImagePromptOut
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


def draft_conflicts(llm, source_text: str) -> list:
    out: ConflictsOut = _ask(llm, read_prompt("conflict_system"), source_text, ConflictsOut)
    if not out.candidates:
        raise ValueError("候选为空")
    return out.candidates


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


def gen_image_prompt(llm, body: str, mood: str) -> str:
    user = read_prompt("image_style").format(body=body, mood=mood)
    out: ImagePromptOut = _ask(llm, "你是专业的人像摄影提示词生成器", user, ImagePromptOut)
    return out.image_prompt.strip()
