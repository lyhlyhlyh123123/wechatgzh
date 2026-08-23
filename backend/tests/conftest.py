import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base


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
def client(test_engine):
    from fastapi.testclient import TestClient

    from app.main import create_app

    Session = sessionmaker(bind=test_engine, autoflush=False)
    app = create_app(session_factory=Session, db_engine=test_engine)
    with TestClient(app) as c:
        yield c
