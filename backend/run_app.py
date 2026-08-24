import os
import shutil
import sys
import threading
import webbrowser
from pathlib import Path


def _provision(bundled_root: Path) -> None:
    for name in ("templates", "static"):
        src = bundled_root / name
        dst = Path.cwd() / name
        if src.exists() and not dst.exists():
            shutil.copytree(src, dst)


def main() -> None:
    if getattr(sys, "frozen", False):
        os.chdir(os.path.dirname(sys.executable))
        internal = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent / "_internal"))
        _provision(internal)

    import uvicorn

    from app.config import settings
    from app.main import app

    url = f"http://127.0.0.1:{settings.port}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
