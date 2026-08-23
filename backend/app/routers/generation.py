from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_presets
from app.database import get_db
from app.schemas import ArticleOut, BuildIn, DraftConflictsIn
from app.services import pipeline

router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generation/draft-conflicts")
def api_draft_conflicts(data: DraftConflictsIn, request: Request, db: Session = Depends(get_db)):
    try:
        candidates = pipeline.draft_conflicts(db, request.app.state.llm, data.topic_id, data.idea)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"生成失败: {exc}")
    return {"candidates": [c.model_dump() for c in candidates]}


@router.post("/generation/build", response_model=ArticleOut)
def api_build(data: BuildIn, request: Request, db: Session = Depends(get_db)):
    try:
        article = pipeline.build_article(
            db, request.app.state.llm, request.app.state.ark, data,
            storage_root=request.app.state.storage_root,
            default_size=request.app.state.default_size,
            max_count=request.app.state.max_count,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"生成失败: {exc}")
    return article


@router.post("/articles/{article_id}/regen-titles", response_model=ArticleOut)
def api_regen_titles(article_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        return pipeline.regen_titles(db, request.app.state.llm, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"生成失败: {exc}")


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
    count = (body or {}).get("count") or 1
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
