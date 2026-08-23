from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.prompt_store import PROMPT_NAMES, read_prompt, write_prompt

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class PromptIn(BaseModel):
    content: str


@router.get("/{name}")
def get_prompt(name: str):
    try:
        return {"name": name, "content": read_prompt(name)}
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.put("/{name}")
def put_prompt(name: str, data: PromptIn):
    try:
        write_prompt(name, data.content)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}
