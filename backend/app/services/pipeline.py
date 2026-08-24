import time
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Article, GenerationLog, Topic
from app.schemas import BuildIn, Candidate
from app.services.prompt_store import read_prompt
from app.services.stages import create_package, gen_body


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
        image_prompt=data.image_prompt,
        question_text=data.question_text,
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


def regen_body(db: Session, llm, article_id: int) -> Article:
    article = get_article(db, article_id)
    t0 = time.time()
    try:
        out = gen_body(llm, article.question_text, article.title)
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


def one_shot_create(db: Session, llm, ark, storage_root: Path,
                    default_size: str, max_count: int,
                    image_count: int = 1,
                    image_preferences: dict | None = None) -> Article:
    bank_text = read_prompt("question_bank")
    used = [
        q for (q,) in db.query(Article.question_text)
        .filter(Article.question_text != "").distinct().all()
        if q
    ]
    package = create_package(llm, bank_text, used, image_preferences)
    data = BuildIn(
        conflict=package.conflict,
        title=package.titles[0],
        candidates=[Candidate(conflict=package.conflict, titles=list(package.titles))],
        image_size=default_size,
        image_count=image_count,
        image_prompt=package.image_prompt,
        question_text=package.question,
    )
    article = build_article(db, llm, ark, data,
                            storage_root=storage_root,
                            default_size=default_size,
                            max_count=max_count)
    if image_preferences:
        article.image_preferences = image_preferences
        db.commit()
        db.refresh(article)
    return article
