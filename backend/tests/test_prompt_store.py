import pytest

from app.services.prompt_store import PROMPT_NAMES, read_prompt, write_prompt


def test_read_all_names():
    for name in PROMPT_NAMES:
        text = read_prompt(name)
        assert isinstance(text, str)
        assert len(text) > 20


def test_write_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import shutil

    from app.config import settings

    src_dir = tmp_path / "tpl_src"
    real_dir = tmp_path / "templates" / "prompts"
    real_dir.mkdir(parents=True)
    real_dir.joinpath("conflict_system.txt").write_text("旧内容", encoding="utf-8")

    write_prompt("conflict_system", "新内容")
    assert read_prompt("conflict_system") == "新内容"

    with pytest.raises(ValueError):
        write_prompt("evil_name", "x")
    with pytest.raises(ValueError):
        read_prompt("evil_name")
