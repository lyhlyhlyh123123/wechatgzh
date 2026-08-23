from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from app.database import Base, SessionLocal, engine, get_db
from app.routers import topics
from app.seed import ensure_seed


def create_app(session_factory: sessionmaker | None = None, db_engine=None) -> FastAPI:
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
    app.include_router(topics.router)
    return app


app = create_app()
