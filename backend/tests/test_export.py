import io
import zipfile

from tests.test_generation_api import BUILD_BODY, wired


def test_export_zip(client, wired):
    art = client.post("/api/generation/build", json=BUILD_BODY).json()
    r = client.get(f"/api/articles/{art['id']}/export.zip")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert "article.md" in names
    images = [n for n in names if n.startswith("images/")]
    assert len(images) == len(art["image_paths"])
    md = zf.read("article.md").decode("utf-8")
    assert md.startswith("# 35岁，我选了稳定")
    assert "以前总觉得" in md


def test_markdown_format(test_session, test_engine):
    from app.database import Base

    Base.metadata.create_all(test_engine)
    from app.models import Article
    from app.services.export import build_markdown

    a = Article(title="标题X", body="正文Y")
    test_session.add(a)
    test_session.commit()
    assert build_markdown(a) == "# 标题X\n\n正文Y"
