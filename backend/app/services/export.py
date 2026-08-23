import io
import zipfile
from pathlib import Path

from app.models import Article


def build_markdown(article: Article) -> str:
    return f"# {article.title}\n\n{article.body}"


def build_zip(article: Article, storage_root: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("article.md", build_markdown(article))
        for rel in article.image_paths or []:
            src = storage_root / rel
            if src.exists():
                zf.write(src, f"images/{src.name}")
    return buf.getvalue()
