from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ArticleOut
from app.services import pipeline

router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/creation/one-shot", response_model=ArticleOut)
def api_one_shot(request: Request, body: dict | None = None,
                 db: Session = Depends(get_db)):
    prefs = (body or {}).get("image_preferences") or {}
    try:
        article = pipeline.one_shot_create(
            db, request.app.state.llm, request.app.state.ark,
            storage_root=request.app.state.storage_root,
            default_size=request.app.state.default_size,
            max_count=request.app.state.max_count,
            image_preferences=prefs,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"生成失败: {exc}")
    return article


@router.post("/articles/{article_id}/regen-body", response_model=ArticleOut)
def api_regen_body(article_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        return pipeline.regen_body(db, request.app.state.llm, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"生成失败: {exc}")


@router.post("/articles/{article_id}/regen-images", response_model=ArticleOut)
def api_regen_images(article_id: int, request: Request, body: dict | None = None,
                     db: Session = Depends(get_db)):
    count = (body or {}).get("count") or request.app.state.default_count
    try:
        return pipeline.regen_images(
            db, request.app.state.ark, article_id, count,
            storage_root=request.app.state.storage_root,
            max_count=request.app.state.max_count,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"生成失败: {exc}")
