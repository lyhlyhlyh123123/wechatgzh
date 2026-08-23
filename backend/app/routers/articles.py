import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article
from app.schemas import ArticleListOut, ArticleOut, ArticlePatch, StatusIn
from app.services import pipeline

router = APIRouter(prefix="/api/articles", tags=["articles"])

VALID_STATUS = {"draft", "approved", "published"}


@router.get("", response_model=ArticleListOut)
def list_articles(status: str | None = None, q: str | None = None,
                  page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    query = db.query(Article)
    if status:
        query = query.filter(Article.status == status)
    if q:
        query = query.filter(Article.title.contains(q))
    total = query.count()
    items = (
        query.order_by(Article.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"total": total, "items": items}


@router.get("/{article_id}", response_model=ArticleOut)
def get_one(article_id: int, db: Session = Depends(get_db)):
    try:
        return pipeline.get_article(db, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.patch("/{article_id}", response_model=ArticleOut)
def patch_article(article_id: int, data: ArticlePatch, db: Session = Depends(get_db)):
    try:
        article = pipeline.get_article(db, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(article, k, v)
    db.commit()
    db.refresh(article)
    return article


@router.post("/{article_id}/status", response_model=ArticleOut)
def set_status(article_id: int, data: StatusIn, db: Session = Depends(get_db)):
    if data.status not in VALID_STATUS:
        raise HTTPException(422, "非法状态")
    try:
        article = pipeline.get_article(db, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    article.status = data.status
    db.commit()
    db.refresh(article)
    return article


@router.delete("/{article_id}", status_code=204)
def delete_article(article_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        article = pipeline.get_article(db, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    folder = Path(request.app.state.storage_root) / "runs" / str(article_id)
    shutil.rmtree(folder, ignore_errors=True)
    db.delete(article)
    db.commit()
