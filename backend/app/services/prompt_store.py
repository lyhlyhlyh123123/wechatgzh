from pathlib import Path

BASE_DIR = Path("templates") / "prompts"
PROMPT_NAMES = ["creator_system", "body_system", "question_bank"]
_EXTENSIONS = {"question_bank": ".json"}


def _check(name: str) -> None:
    if name not in PROMPT_NAMES:
        raise ValueError(f"未知提示词: {name}")


def _path(name: str) -> Path:
    return BASE_DIR / f"{name}{_EXTENSIONS.get(name, '.txt')}"


def read_prompt(name: str) -> str:
    _check(name)
    path = _path(name)
    if not path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def write_prompt(name: str, text: str) -> None:
    _check(name)
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    _path(name).write_text(text, encoding="utf-8")
