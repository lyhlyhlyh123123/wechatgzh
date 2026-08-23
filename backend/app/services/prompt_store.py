from pathlib import Path

BASE_DIR = Path("templates") / "prompts"
PROMPT_NAMES = ["conflict_system", "body_system", "image_style"]


def _check(name: str) -> None:
    if name not in PROMPT_NAMES:
        raise ValueError(f"未知提示词: {name}")


def read_prompt(name: str) -> str:
    _check(name)
    path = BASE_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def write_prompt(name: str, text: str) -> None:
    _check(name)
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / f"{name}.txt").write_text(text, encoding="utf-8")
