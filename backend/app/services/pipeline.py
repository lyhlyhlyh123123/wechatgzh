import time
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Article, GenerationLog, Topic
from app.schemas import BuildIn
from app.services.stages import draft_conflicts as _stage_conflicts
from app.services.stages import gen_body, gen_image_prompt


def _model_name(llm) -> str:
    return str(getattr(llm, "model", ""))


def _log(db: Session, article_id: int | None, stage: str, llm, t0: float,
         ok: bool = True, error: str | None = None) -> None:
    db.add(GenerationLog(
        article_id=article_id,
        stage=stage,
        model=_model_name(llm),
        ok=ok,
        error=error,
        elapsed_ms=int((time.time() - t0) * 1000),
    ))
    db.commit()


def source_text(db: Session, topic_id: int | None = None, idea: str = "") -> str:
    if topic_id:
        topic = db.get(Topic, topic_id)
        if not topic:
            raise ValueError("主题不存在")
        return f"驱动类型：{topic.drive_type}\n分类：{topic.category}\n素材：{topic.conflict}"
    if not idea.strip():
        raise ValueError("必须提供主题或想法")
    return f"自由想法：{idea.strip()}"


def draft_conflicts(db: Session, llm, topic_id: int | None = None, idea: str = "") -> list:
    text = source_text(db, topic_id, idea)
    t0 = time.time()
    try:
        candidates = _stage_conflicts(llm, text)
        _log(db, None, "conflict", llm, t0)
        return candidates
    except Exception as exc:
        _log(db, None, "conflict", llm, t0, ok=False, error=str(exc))
        raise


def generate_images(ark, article: Article, count: int, storage_root: Path) -> list[str]:
    folder = Path(storage_root) / "runs" / str(article.id)
    paths = []
    for i in range(count):
        fname = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}.jpg"
        ark.generate_image(article.image_prompt, article.image_size, folder / fname)
        paths.append(f"runs/{article.id}/{fname}")
    return paths


def build_article(db: Session, llm, ark, data: BuildIn, storage_root: Path,
                  default_size: str = "1080x1620", max_count: int = 3) -> Article:
    article = Article(
        topic_id=data.topic_id,
        title=data.title.strip(),
        image_size=data.image_size or default_size,
    )
    if data.candidates:
        article.title_candidates = [c.model_dump() for c in data.candidates]
    else:
        article.title_candidates = [{"conflict": data.conflict, "titles": [data.title]}]
    db.add(article)
    db.commit()
    db.refresh(article)

    t0 = time.time()
    try:
        body_out = gen_body(llm, data.conflict, article.title)
    except Exception as exc:
        _log(db, article.id, "body", llm, t0, ok=False, error=str(exc))
        raise
    article.body = body_out.body
    article.mood = body_out.mood
    _log(db, article.id, "body", llm, t0)
    db.commit()

    t0 = time.time()
    try:
        article.image_prompt = gen_image_prompt(llm, article.body, article.mood)
    except Exception as exc:
        _log(db, article.id, "image_prompt", llm, t0, ok=False, error=str(exc))
        raise
    _log(db, article.id, "image_prompt", llm, t0)
    db.commit()

    count = min(max(data.image_count or 1, 1), max_count)
    t0 = time.time()
    try:
        article.image_paths = generate_images(ark, article, count, storage_root)
    except Exception as exc:
        _log(db, article.id, "image", llm, t0, ok=False, error=str(exc))
        raise
    _log(db, article.id, "image", llm, t0)
    db.commit()

    if data.topic_id:
        topic = db.get(Topic, data.topic_id)
        if topic:
            topic.use_count += 1
            db.commit()
    return article


def get_article(db: Session, article_id: int) -> Article:
    article = db.get(Article, article_id)
    if not article:
        raise ValueError(f"内容包不存在: {article_id}")
    return article


def _current_conflict(article: Article) -> str:
    for cand in article.title_candidates or []:
        if isinstance(cand, dict) and article.title in cand.get("titles", []):
            return cand.get("conflict", "")
    first = article.title_candidates[0] if article.title_candidates else {}
    return first.get("conflict", "") if isinstance(first, dict) else ""


def regen_titles(db: Session, llm, article_id: int) -> Article:
    article = get_article(db, article_id)
    src = (
        f"现有标题：{article.title}\n"
        f"冲突方向：{_current_conflict(article)}\n"
        f"正文片段：{article.body[:50]}"
    )
    t0 = time.time()
    try:
        candidates = _stage_conflicts(llm, src)
        article.title_candidates = [c.model_dump() for c in candidates]
    except Exception as exc:
        _log(db, article.id, "titles_regen", llm, t0, ok=False, error=str(exc))
        raise
    _log(db, article.id, "titles_regen", llm, t0)
    db.commit()
    db.refresh(article)
    return article


def regen_body(db: Session, llm, article_id: int) -> Article:
    article = get_article(db, article_id)
    t0 = time.time()
    try:
        out = gen_body(llm, _current_conflict(article), article.title)
        article.body = out.body
        article.mood = out.mood
    except Exception as exc:
        _log(db, article.id, "body_regen", llm, t0, ok=False, error=str(exc))
        raise
    _log(db, article.id, "body_regen", llm, t0)
    db.commit()
    db.refresh(article)
    return article


def regen_images(db: Session, ark, article_id: int, count: int,
                 storage_root: Path, max_count: int = 3) -> Article:
    article = get_article(db, article_id)
    n = min(max(count, 1), max_count)
    article.image_paths = generate_images(ark, article, n, storage_root)
    db.commit()
    db.refresh(article)
    return article
