from app.database import Base
from app.models import Article, GenerationLog, Topic


def test_tables_exist(test_engine):
    assert {"topics", "articles", "generation_logs"} <= set(Base.metadata.tables)


def test_defaults(test_session):
    t = Topic(drive_type="恐惧", category="情感关系", conflict="如果一直遇不到合适的人，该怎么办")
    test_session.add(t)
    a = Article(title="38岁单身，我是不是错过爱情了")
    test_session.add(a)
    g = GenerationLog(stage="body")
    test_session.add(g)
    test_session.commit()
    assert t.enabled is True
    assert t.use_count == 0
    assert a.status == "draft"
    assert a.image_paths == []
    assert a.title_candidates == []
    assert a.image_size == "1080x1620"
    assert g.ok is True
