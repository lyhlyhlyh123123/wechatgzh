import os

os.environ["WECHATGZH_AUTO_CREATE"] = "0"

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base


class _LLM:
    model = "unwired"

    def chat_json(self, system, user, temperature=0.8):
        raise RuntimeError("测试未注入 LLM 响应")


class _Ark:
    def generate_image(self, prompt, size, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"img")
        return output_path


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture
def test_session(test_engine):
    Session = sessionmaker(bind=test_engine, autoflush=False)
    s = Session()
    yield s
    s.close()


@pytest.fixture
def client(test_engine, tmp_path_factory):
    from fastapi.testclient import TestClient

    from app.main import create_app

    Session = sessionmaker(bind=test_engine, autoflush=False)
    storage_root = tmp_path_factory.mktemp("storage")
    app = create_app(
        session_factory=Session,
        db_engine=test_engine,
        llm=_LLM(),
        ark=_Ark(),
        storage_root=str(storage_root),
    )
    with TestClient(app) as c:
        c.storage_root = storage_root
        yield c
