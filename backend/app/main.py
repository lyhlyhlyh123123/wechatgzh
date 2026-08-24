from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from app.clients.ark import ArkClient
from app.clients.deepseek import DeepSeekClient
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.routers import articles, generation, prompts_api, settings_api, topics
from app.seed import ensure_seed


def create_app(session_factory: sessionmaker | None = None, llm=None, ark=None,
               storage_root: str = "storage", db_engine=None) -> FastAPI:
    app = FastAPI(title="wechatgzh")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def override_session():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    if session_factory is not None:
        app.dependency_overrides[get_db] = override_session

    eng = db_engine or engine
    Base.metadata.create_all(eng)
    SF = session_factory or SessionLocal
    with SF() as db:
        ensure_seed(db)

    app.state.llm = llm or DeepSeekClient(
        settings.deepseek_base_url,
        settings.deepseek_api_key,
        settings.deepseek_model,
    )
    app.state.ark = ark or ArkClient(
        settings.volcengine_ark_base_url,
        settings.volcengine_ark_api_key,
        settings.volcengine_ark_image_model,
    )
    app.state.storage_root = storage_root
    app.state.default_size = settings.image_size_default
    app.state.max_count = settings.image_count_max

    app.include_router(topics.router)
    app.include_router(generation.router)
    app.include_router(articles.router)
    app.include_router(prompts_api.router)
    app.include_router(settings_api.router)

    storage_dir = Path(storage_root)
    storage_dir.mkdir(exist_ok=True)
    app.mount("/files", StaticFiles(directory=str(storage_dir)), name="files")

    static_dir = Path("static")
    if (static_dir / "index.html").exists():

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            target = static_dir / full_path
            if full_path and target.is_file():
                return FileResponse(target)
            return FileResponse(static_dir / "index.html")
    return app


import os

if os.environ.get("WECHATGZH_AUTO_CREATE", "1") == "1":
    app = create_app()