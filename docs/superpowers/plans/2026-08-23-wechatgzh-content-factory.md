# 微信公众号情感内容生产工作台 · 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建本地 Web 工作台，一键生成「情感冲突 + 标题候选 + 第一人称短文案（30–60字）+ 真实感女性配图」的公众号贴图内容包，支持局部重生、人工审核状态流转、导出。

**Architecture:** FastAPI 单体后端（SQLAlchemy + SQLite；DeepSeek 生成文字、火山 ARK 生成图片），Vue3 + Element Plus 工作台前端。生成流程拆为独立 stage 纯函数，支持逐环节重跑；提示词外置可热改。

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy 2 / pydantic-settings / httpx / tenacity / pytest；Vue 3 / Vite / Element Plus / Pinia / vue-router / axios

**设计文档:** `docs/superpowers/specs/2026-08-23-wechatgzh-content-factory-design.md`

## Global Constraints

- 运行环境 Windows + PowerShell。后端命令在 `backend/` 目录执行，前端命令在 `frontend/` 目录执行
- Python ≥3.11，Node ≥18
- 所有界面文案使用中文
- 正文长度约束：30–60 字
- 图片默认 2:3 竖版长图 1080×1620，数量默认 1、最大 3；预设：`2:3_1080x1620,1:1_1080x1080,3:4_750x1000,16:9_1920x1080,9:16_1080x1920`
- 内容包状态机：`draft / approved / published`，手动流转、允许任意回退
- 提示词外置于 `backend/templates/prompts/*.txt`，修改即生效（每次调用现读）
- 代码不加注释
- 不引入本计划依赖清单之外的第三方库
- 每个 Task 结束必须 git commit

### v1.1 追加约束（Task 15–17）

- 100 个情感问题完整内置于 `backend/templates/question_bank.json`，作为选题灵感库唯一来源之一
- 自动选题不得选中已被任何内容包关联过的主题；发布过的问题因此天然不可重复
- `ensure_seed` 必须增量幂等：按 conflict 文本判重插入，重复运行不产生重复行

## File Structure

```
backend/
├── pyproject.toml
├── .env.example
├── app/
│   ├── __init__.py
│   ├── config.py            # Settings + get_presets()
│   ├── database.py          # engine/SessionLocal/Base/get_db
│   ├── models.py            # Topic / Article / GenerationLog
│   ├── schemas.py           # Pydantic 模型（含 LLM 输出校验）
│   ├── seed.py              # 主题库种子数据（幂等）
│   ├── main.py              # create_app 工厂
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── deepseek.py      # DeepSeekClient.chat_json
│   │   └── ark.py           # ArkClient.generate_image
│   ├── services/
│   │   ├── __init__.py
│   │   ├── prompt_store.py  # 提示词读取/保存（白名单）
│   │   ├── stages.py        # 冲突标题/正文/图片prompt 三个纯函数
│   │   ├── pipeline.py      # 一键成稿 + 局部重生 + 生成日志
│   │   ├── export.py        # article.md + zip
│   │   └── envfile.py       # .env 读写（设置持久化）
│   └── routers/
│       ├── __init__.py
│       ├── topics.py
│       ├── articles.py      # 列表/详情/PATCH/删除/状态/导出
│       ├── generation.py    # draft-conflicts / build / regen-*
│       ├── prompts_api.py
│       └── settings_api.py
├── templates/prompts/
│   ├── conflict_system.txt
│   ├── body_system.txt
│   └── image_style.txt
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_topics.py
│   ├── test_clients.py
│   ├── test_prompt_store.py
│   ├── test_stages.py
│   ├── test_pipeline.py
│   ├── test_generation_api.py
│   ├── test_articles_api.py
│   └── test_export.py
├── storage/runs/            # gitignore；图片产物
├── data/                    # gitignore；app.db
└── static/                  # gitignore；前端构建产物
frontend/
├── vite.config.js
└── src/
    ├── main.js
    ├── App.vue
    ├── api.js
    ├── router.js
    └── views/
        ├── HomeView.vue
        ├── WizardView.vue
        ├── DetailView.vue
        ├── TopicsView.vue
        └── SettingsView.vue
```

---

### Task 1: 后端骨架 + 配置 + 数据模型

**Files:**
- Create: `backend/pyproject.toml`, `backend/.env.example`, `backend/.gitignore`, `backend/app/__init__.py`(空), `backend/tests/__init__.py`(空), `backend/app/config.py`, `backend/app/database.py`, `backend/app/models.py`
- Test: `backend/tests/conftest.py`, `backend/tests/test_models.py`

**Interfaces:**
- Produces: `settings`（Settings 实例）；`get_presets() -> list[dict]`（label/size）；`Base`/`engine`/`SessionLocal`/`get_db()`；ORM 类 `Topic`/`Article`/`GenerationLog`

- [ ] **Step 1: 创建依赖清单与环境**

`backend/pyproject.toml`：

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "wechatgzh-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "uvicorn>=0.30",
  "sqlalchemy>=2.0",
  "pydantic>=2.8",
  "pydantic-settings>=2.4",
  "httpx>=0.27",
  "tenacity>=8.5",
]

[project.optional-dependencies]
dev = ["pytest>=8.3"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`backend/.env.example`：

```
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
VOLCENGINE_ARK_API_KEY=
VOLCENGINE_ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
VOLCENGINE_ARK_IMAGE_MODEL=
IMAGE_PRESET=2:3_1080x1620,1:1_1080x1080,3:4_750x1000,16:9_1920x1080,9:16_1080x1920
IMAGE_SIZE_DEFAULT=1080x1620
IMAGE_COUNT_DEFAULT=1
IMAGE_COUNT_MAX=3
HOST=127.0.0.1
PORT=8000
```

`backend/.gitignore`：

```
.env
data/
storage/
static/
__pycache__/
.pytest_cache/
*.egg-info/
.venv/
```

安装命令（在 backend 目录）：

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```

Run: `.venv\Scripts\python -c "import fastapi, sqlalchemy, httpx; print('ok')"`
Expected: `ok`

- [ ] **Step 2: 写失败测试**

`backend/tests/conftest.py`：

```python
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
    app = create_app(session_factory=Session)
    with TestClient(app) as c:
        yield c
```

`backend/tests/test_models.py`：

```python
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
```

- [ ] **Step 3: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_models.py -v`
Expected: FAIL（ModuleNotFoundError 或 ImportError）

- [ ] **Step 4: 实现 config / database / models**

`backend/app/config.py`：

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    volcengine_ark_api_key: str = ""
    volcengine_ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    volcengine_ark_image_model: str = ""
    image_preset: str = "2:3_1080x1620,1:1_1080x1080,3:4_750x1000,16:9_1920x1080,9:16_1080x1920"
    image_size_default: str = "1080x1620"
    image_count_default: int = 1
    image_count_max: int = 3
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def get_presets() -> list[dict]:
    result = []
    for item in settings.image_preset.split(","):
        label, _, size = item.strip().partition("_")
        if label and size:
            result.append({"label": label, "size": size})
    return result
```

`backend/app/database.py`：

```python
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

Path("data").mkdir(parents=True, exist_ok=True)

engine = create_engine(
    "sqlite:///data/app.db",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`backend/app/models.py`：

```python
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    drive_type: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(50))
    conflict: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    title_candidates: Mapped[list] = mapped_column(JSON, default=list)
    body: Mapped[str] = mapped_column(Text, default="")
    mood: Mapped[str] = mapped_column(String(50), default="")
    image_prompt: Mapped[str] = mapped_column(Text, default="")
    image_paths: Mapped[list] = mapped_column(JSON, default=list)
    image_size: Mapped[str] = mapped_column(String(20), default="1080x1620")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stage: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100), default="")
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_models.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```powershell
git add -A
git commit -m "feat: 后端骨架、配置与数据模型"
```

### Task 2: 主题库种子数据 + CRUD 接口 + 最小 main

**Files:**
- Create: `backend/app/schemas.py`, `backend/app/seed.py`, `backend/app/routers/__init__.py`(空), `backend/app/routers/topics.py`, `backend/app/main.py`
- Test: `backend/tests/test_topics.py`

**Interfaces:**
- Consumes: Task 1 的 `Topic`/`get_db`/`Base`
- Produces: `/api/topics` REST（返回 `{total, items}`）；`ensure_seed(session)` 幂等种子；`create_app(session_factory=None)` 工厂（后续所有 API 测试依赖）

- [ ] **Step 1: 写失败测试**

`backend/tests/test_topics.py`：

```python
from app.models import Topic
from app.seed import ensure_seed


def test_seed_visible_via_api(client):
    data = client.get("/api/topics").json()
    assert data["total"] >= 10


def test_seed_idempotent(test_session):
    ensure_seed(test_session)
    ensure_seed(test_session)
    assert test_session.query(Topic).count() >= 10


def test_topic_crud(client):
    r = client.post(
        "/api/topics",
        json={"drive_type": "站队", "category": "婚姻", "conflict": "爱情还是稳定"},
    )
    assert r.status_code == 200
    tid = r.json()["id"]
    assert r.json()["enabled"] is True

    r = client.patch(f"/api/topics/{tid}", json={"enabled": False})
    assert r.json()["enabled"] is False

    r = client.get("/api/topics", params={"drive_type": "站队"})
    assert any(t["id"] == tid for t in r.json()["items"])

    assert client.delete(f"/api/topics/{tid}").status_code == 204
```

说明：`client` fixture（conftest，见 Task 1）把内存 engine 传给 `create_app(db_engine=...)`，种子写入内存库，测试互不污染、不触碰文件库。

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_topics.py -v`
Expected: FAIL（ImportError: cannot import name 'create_app'）

- [ ] **Step 3: 实现 schemas / seed / topics / main**

`backend/app/schemas.py`：

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TopicIn(BaseModel):
    drive_type: str = Field(min_length=1, max_length=20)
    category: str = Field(min_length=1, max_length=50)
    conflict: str = Field(min_length=1)


class TopicPatch(BaseModel):
    drive_type: str | None = None
    category: str | None = None
    conflict: str | None = None
    enabled: bool | None = None


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    drive_type: str
    category: str
    conflict: str
    enabled: bool
    use_count: int


class TopicListOut(BaseModel):
    total: int
    items: list[TopicOut]


class Candidate(BaseModel):
    conflict: str
    titles: list[str]


class ConflictsOut(BaseModel):
    candidates: list[Candidate]


class BodyOut(BaseModel):
    body: str
    mood: str


class ImagePromptOut(BaseModel):
    image_prompt: str


class DraftConflictsIn(BaseModel):
    topic_id: int | None = None
    idea: str = ""


class BuildIn(BaseModel):
    topic_id: int | None = None
    conflict: str
    title: str
    image_size: str | None = None
    image_count: int | None = None


class ArticlePatch(BaseModel):
    title: str | None = None
    body: str | None = None
    image_prompt: str | None = None
    image_size: str | None = None


class StatusIn(BaseModel):
    status: str


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int | None
    title: str
    title_candidates: list
    body: str
    mood: str
    image_prompt: str
    image_paths: list
    image_size: str
    status: str
    created_at: datetime
    updated_at: datetime


class ArticleListOut(BaseModel):
    total: int
    items: list[ArticleOut]


class TitleCandidatesOut(BaseModel):
    candidates: list[str]
```

`backend/app/seed.py`：

```python
from sqlalchemy.orm import Session

from app.models import Topic

SEED_TOPICS = [
    ("欲望", "情感关系", "越成熟的女人越有魅力，是被生活打磨出来的"),
    ("比较", "年龄变化", "同龄人都结婚生子了，我还在等什么"),
    ("恐惧", "情感关系", "如果一直遇不到合适的人，该怎么办"),
    ("窥私", "婚姻", "一个40岁的女人离婚后，过得好吗"),
    ("站队", "婚姻", "婚姻应该选择爱情，还是稳定"),
    ("比较", "女性成长", "月薪五万以后，为什么还是不快乐"),
    ("恐惧", "年龄变化", "35岁以后，是不是就没有资格挑了"),
    ("欲望", "两性关系", "被选择和主动选择，哪个更让人安心"),
    ("窥私", "成年人的现实", "那些嫁得好的女生，后来都怎么样了"),
    ("站队", "情感关系", "心动和稳定，只能选一个"),
    ("比较", "人生阶段", "38岁还单身，真的比结婚晚了吗"),
    ("恐惧", "成年人的现实", "存款和安全感，到底哪个先来"),
]


def ensure_seed(session: Session) -> None:
    if session.query(Topic).count() > 0:
        return
    for drive_type, category, conflict in SEED_TOPICS:
        session.add(Topic(drive_type=drive_type, category=category, conflict=conflict))
    session.commit()
```

`backend/app/routers/topics.py`：

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Topic
from app.schemas import TopicIn, TopicListOut, TopicOut, TopicPatch

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("", response_model=TopicListOut)
def list_topics(drive_type: str | None = None, enabled: bool | None = None, db: Session = Depends(get_db)):
    q = db.query(Topic)
    if drive_type:
        q = q.filter(Topic.drive_type == drive_type)
    if enabled is not None:
        q = q.filter(Topic.enabled == enabled)
    items = q.order_by(Topic.id).all()
    return {"total": len(items), "items": items}


@router.post("", response_model=TopicOut)
def create_topic(data: TopicIn, db: Session = Depends(get_db)):
    topic = Topic(**data.model_dump())
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.patch("/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: int, data: TopicPatch, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "主题不存在")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(topic, k, v)
    db.commit()
    db.refresh(topic)
    return topic


@router.delete("/{topic_id}", status_code=204)
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "主题不存在")
    db.delete(topic)
    db.commit()
```

`backend/app/main.py`：

```python
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
```

conftest 的 `client` fixture 相应传入 engine（此处先给 Task 2 阶段的临时版，Task 7 会给出含 llm/ark/storage 的最终完整版）：

```python
    app = create_app(session_factory=Session, db_engine=test_engine)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_topics.py tests/test_models.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "feat: 主题库种子数据与CRUD接口、应用工厂"
```

---

### Task 3: DeepSeek 与 ARK 客户端

**Files:**
- Create: `backend/app/clients/__init__.py`(空), `backend/app/clients/deepseek.py`, `backend/app/clients/ark.py`
- Test: `backend/tests/test_clients.py`

**Interfaces:**
- Produces:
  - `DeepSeekClient(base_url, api_key, model).chat_json(system: str, user: str, temperature: float = 0.8) -> dict`
  - `ArkClient(base_url, api_key, model).generate_image(prompt: str, size: str, output_path: Path) -> Path`
  - 两者均接受可选 `transport: httpx.BaseTransport`（测试注入 MockTransport）

- [ ] **Step 1: 写失败测试**

`backend/tests/test_clients.py`：

```python
import base64

import httpx
import pytest

from app.clients.ark import ArkClient
from app.clients.deepseek import DeepSeekClient


def test_deepseek_chat_json_parses():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-test"
        body = {
            "choices": [{"message": {"content": '{"a": 1}'}}],
        }
        return httpx.Response(200, json=body)

    client = DeepSeekClient(
        "https://fake", "sk-test", "deepseek-chat",
        transport=httpx.MockTransport(handler),
    )
    assert client.chat_json("sys", "user") == {"a": 1}


def test_deepseek_retries_on_bad_json():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        content = "{bad" if calls["n"] < 2 else '{"ok": true}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = DeepSeekClient(
        "https://fake", "k", "m",
        transport=httpx.MockTransport(handler), retries=2,
    )
    assert client.chat_json("s", "u") == {"ok": True}
    assert calls["n"] == 2


def test_ark_saves_b64_image(tmp_path):
    png = base64.b64encode(b"fakebytes").decode()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = request.read()
        assert b'"1080x1620"' in payload
        return httpx.Response(200, json={"data": [{"b64_json": png}]})

    out = tmp_path / "img.jpg"
    client = ArkClient(
        "https://fake", "k", "model-x",
        transport=httpx.MockTransport(handler),
    )
    result = client.generate_image("prompt text", "1080x1620", out)
    assert result.exists()
    assert result.read_bytes() == b"fakebytes"


def test_ark_downloads_url(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/images/generations"):
            return httpx.Response(200, json={"data": [{"url": "https://fake/dl"}]})
        return httpx.Response(200, content=b"urlbytes")

    out = tmp_path / "img.jpg"
    client = ArkClient(
        "https://fake", "k", "m",
        transport=httpx.MockTransport(handler),
    )
    client.generate_image("p", "1080x1620", out)
    assert out.read_bytes() == b"urlbytes"


def test_ark_raises_when_empty(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    client = ArkClient(
        "https://fake", "k", "m",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(RuntimeError):
        client.generate_image("p", "1080x1620", tmp_path / "x.jpg")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_clients.py -v`
Expected: FAIL（ModuleNotFoundError: app.clients）

- [ ] **Step 3: 实现两个客户端**

`backend/app/clients/deepseek.py`：

```python
from __future__ import annotations

import json

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


class DeepSeekError(Exception):
    pass


class DeepSeekClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
        retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.transport = transport
        self.retries = retries

    def chat_json(self, system: str, user: str, temperature: float = 0.8) -> dict:
        attempt = self._call_with_retry
        return attempt(system, user, temperature)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type((DeepSeekError, json.JSONDecodeError)),
    )
    def _call_with_retry(self, system: str, user: str, temperature: float) -> dict:
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()
        try:
            content = raw["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise DeepSeekError(f"LLM 响应解析失败: {exc}") from exc
```

注意 `retries` 参数与装饰器静态值冲突：装饰器固定 3 次。为让测试的 `retries=2` 生效且保持简单，改为循环实现，不用 tenacity 装饰器：

```python
from __future__ import annotations

import json
import time

import httpx


class DeepSeekError(Exception):
    pass


class DeepSeekClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
        retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.transport = transport
        self.retries = retries

    def chat_json(self, system: str, user: str, temperature: float = 0.8) -> dict:
        last_exc: Exception | None = None
        for i in range(self.retries):
            try:
                return self._once(system, user, temperature)
            except (DeepSeekError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if i < self.retries - 1:
                    time.sleep(1)
        raise DeepSeekError(f"生成失败（已重试{self.retries}次）: {last_exc}")

    def _once(self, system: str, user: str, temperature: float) -> dict:
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()
        try:
            content = raw["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise DeepSeekError(f"LLM 响应解析失败: {exc}") from exc
```

采用第二版（循环重试），删除第一版带 tenacity 的实现。

`backend/app/clients/ark.py`：

```python
from __future__ import annotations

import base64
from pathlib import Path

import httpx


class ArkClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 180.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.transport = transport

    def generate_image(self, prompt: str, size: str, output_path: Path) -> Path:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
            "response_format": "b64_json",
            "watermark": False,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            resp = client.post(f"{self.base_url}/images/generations", headers=headers, json=payload)
            resp.raise_for_status()
            raw = resp.json()

        data = raw.get("data") or []
        if not data:
            raise RuntimeError("ARK 未返回图片数据")

        item = data[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if item.get("b64_json"):
            output_path.write_bytes(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            dl = client.get(item["url"])
            dl.raise_for_status()
            output_path.write_bytes(dl.content)
        else:
            raise RuntimeError("ARK 响应缺少图片内容")
        return output_path
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_clients.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "feat: DeepSeek与ARK客户端"
```

### Task 4: 提示词模板与读写接口

**Files:**
- Create: `backend/templates/prompts/conflict_system.txt`, `backend/templates/prompts/body_system.txt`, `backend/templates/prompts/image_style.txt`, `backend/app/services/__init__.py`(空), `backend/app/services/prompt_store.py`, `backend/app/routers/prompts_api.py`
- Test: `backend/tests/test_prompt_store.py`

**Interfaces:**
- Produces: `PROMPT_NAMES = ["conflict_system", "body_system", "image_style"]`；`read_prompt(name) -> str`；`write_prompt(name, text) -> None`（均相对 `templates/prompts/`，路径以 backend 工作目录为准）；REST `/api/prompts/{name}` GET/PUT
- 提示词内容要求：`body_system.txt` 约束正文 30–60 字；`image_style.txt` 含 `{mood}` 与 `{body}` 占位符（stages 用 `.format` 渲染）

- [ ] **Step 1: 写失败测试**

`backend/tests/test_prompt_store.py`：

```python
import pytest

from app.services.prompt_store import PROMPT_NAMES, read_prompt, write_prompt


def test_read_all_names():
    for name in PROMPT_NAMES:
        text = read_prompt(name)
        assert isinstance(text, str)
        assert len(text) > 20


def test_write_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import shutil

    from app.config import settings

    src_dir = tmp_path / "tpl_src"
    real_dir = tmp_path / "templates" / "prompts"
    real_dir.mkdir(parents=True)
    real_dir.joinpath("conflict_system.txt").write_text("旧内容", encoding="utf-8")

    write_prompt("conflict_system", "新内容")
    assert read_prompt("conflict_system") == "新内容"

    with pytest.raises(ValueError):
        write_prompt("evil_name", "x")
    with pytest.raises(ValueError):
        read_prompt("evil_name")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_prompt_store.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 创建三个提示词文件与实现**

`backend/templates/prompts/conflict_system.txt`：

```
你是深谙人性的情感内容策划。基于给定的主题素材，产出3个互相独立的「成年人情感冲突」，每个冲突配5个公众号标题。

规则：
1. 冲突要具体、有画面感，来自真实生活处境（年龄、婚姻、选择、孤独、现实与爱情的拉扯）
2. 标题公式 = 年龄或身份 + 个人状态 + 冲突疑问；第一人称视角；不喊口号、不讲道理、不写观点文标题
3. 标题长度12~22字，结尾用问句或留白陈述
4. 内容面向25~50岁读者，克制、真实、不低俗

只输出JSON，格式：
{"candidates": [{"conflict": "一句话冲突描述", "titles": ["标题1","标题2","标题3","标题4","标题5"]}]}
```

`backend/templates/prompts/body_system.txt`：

```
你是一位38岁的都市女性本人，在写一条朋友圈长文式的短文案。

给定冲突与标题，写第一人称正文。

硬性规则：
1. 总长度30~60个汉字（标点不计），绝对不许超过60字
2. 结构暗线：过去→变化→矛盾→困惑，但不要写出"过去/后来"这种模板词堆砌，行文自然
3. 真人口吻，有具体生活细节，像深夜随手写的，不是鸡汤、不是散文、不说教
4. 结尾停在困惑或半句话上，留白，不给答案，不加提问
5. 同时给出一个2~6字的画面情绪标签(mood)，例如：黄昏阳台、雨夜车内、清晨厨房、深夜路灯

只输出JSON：{"body": "正文", "mood": "情绪标签"}
```

`backend/templates/prompts/image_style.txt`：

```
根据信息生成一张图片提示词（英文），用于真实感人像摄影模型。

正文内容：{body}
画面情绪：{mood}

要求：
1. 一位30~45岁中国女性，气质成熟知性，妆容干净，穿着日常得体
2. 场景与"{mood}"匹配的城市场景，手机抓拍质感、自然光、浅景深、生活感构图
3. 像朋友随手拍的生活照：真实皮肤质感，不完美但动人；绝无明星脸、网红脸、影楼写真感
4. 输出一段60词以内的英文prompt，直接可用的摄影描述词，不要任何解释
```

`backend/app/services/prompt_store.py`：

```python
from pathlib import Path

BASE_DIR = Path("templates") / "prompts"
PROMPT_NAMES = ["conflict_system", "body_system", "image_style"]


def _check(name: str) -> None:
    if name not in PROMPT_NAMES:
        raise ValueError(f"未知提示词: {name}")


def read_prompt(name: str) -> str:
    _check(name)
    path = BASE_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"提示词文件不存在: {path}")
    return path.read_text(encoding="utf-8")


def write_prompt(name: str, text: str) -> None:
    _check(name)
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / f"{name}.txt").write_text(text, encoding="utf-8")
```

注意：`test_read_all_names` 不 chdir，依赖 backend 工作目录下真实存在的模板文件——运行 pytest 时 cwd 是 backend/，成立。`test_write_roundtrip` 用 chdir 隔离写测试。

`backend/app/routers/prompts_api.py`：

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.prompt_store import PROMPT_NAMES, read_prompt, write_prompt

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class PromptIn(BaseModel):
    content: str


@router.get("/{name}")
def get_prompt(name: str):
    try:
        return {"name": name, "content": read_prompt(name)}
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.put("/{name}")
def put_prompt(name: str, data: PromptIn):
    try:
        write_prompt(name, data.content)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_prompt_store.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "feat: 外置提示词模板与读写接口"
```

---

### Task 5: 生成阶段纯函数 stages

**Files:**
- Create: `backend/app/services/stages.py`
- Test: `backend/tests/test_stages.py`

**Interfaces:**
- Consumes: `DeepSeekClient.chat_json`（鸭子类型，测试用 FakeLLM）；schemas 的 `ConflictsOut/BodyOut/ImagePromptOut`
- Produces:
  - `draft_conflicts(llm, source_text: str) -> list[Candidate]`
  - `gen_body(llm, conflict: str, title: str) -> BodyOut`
  - `gen_image_prompt(llm, body: str, mood: str) -> str`
  - 校验失败抛 `ValueError`（由 pipeline 记日志并重试）

- [ ] **Step 1: 写失败测试**

`backend/tests/test_stages.py`：

```python
import pytest

from app.schemas import Candidate
from app.services.stages import draft_conflicts, gen_body, gen_image_prompt


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat_json(self, system, user, temperature=0.8):
        self.calls.append((system, user, temperature))
        return self.responses.pop(0)


def test_draft_conflicts_ok():
    llm = FakeLLM([{
        "candidates": [
            {"conflict": "c1", "titles": ["t1", "t2", "t3", "t4", "t5"]},
            {"conflict": "c2", "titles": ["a", "b", "c", "d", "e"]},
        ]
    }])
    out = draft_conflicts(llm, "主题：恐惧\n素材：遇不到合适的人")
    assert isinstance(out[0], Candidate)
    assert len(out) == 2
    assert "遇不到合适的人" in llm.calls[0][1]


def test_draft_conflicts_retries_on_bad_shape():
    llm = FakeLLM([
        {"wrong": 1},
        {"candidates": [{"conflict": "c", "titles": ["t1", "t2", "t3", "t4", "t5"]}]},
    ])
    out = draft_conflicts(llm, "x")
    assert len(llm.calls) == 2


def test_gen_body():
    llm = FakeLLM([{"body": "以前总觉得来日方长。" * 2, "mood": "黄昏阳台"}])
    out = gen_body(llm, "冲突", "标题")
    assert len(out.body) >= 10
    assert out.mood == "黄昏阳台"


def test_gen_body_enforces_length_after_retry():
    long_body = "字" * 80
    llm = FakeLLM([
        {"body": long_body, "mood": "m"},
        {"body": "三十字左右的正常正文内容大概就是这样了", "mood": "m"},
    ])
    out = gen_body(llm, "c", "t")
    assert len(out.body) <= 60


def test_gen_image_prompt_formats_template(monkeypatch):
    from app.services import stages

    monkeypatch.setattr(
        stages, "read_prompt",
        lambda name: "MOOD={mood} BODY={body}",
    )
    llm = FakeLLM([{"image_prompt": "photo of a woman"}])
    prompt = gen_image_prompt(llm, "正文内容", "雨夜车内")
    assert prompt == "photo of a woman"
    user_msg = llm.calls[0][1]
    assert "雨夜车内" in user_msg and "正文内容" in user_msg
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_stages.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 stages**

`backend/app/services/stages.py`：

```python
import json

from pydantic import ValidationError

from app.schemas import BodyOut, ConflictsOut, ImagePromptOut
from app.services.prompt_store import read_prompt

MAX_ATTEMPTS = 3


def _ask(llm, system: str, user: str, schema):
    last_err: Exception | None = None
    for _ in range(MAX_ATTEMPTS):
        raw = llm.chat_json(system, user)
        try:
            return schema.model_validate(raw)
        except ValidationError as exc:
            last_err = exc
    raise ValueError(f"输出不符合约定结构: {last_err}")


def draft_conflicts(llm, source_text: str) -> list:
    out: ConflictsOut = _ask(llm, read_prompt("conflict_system"), source_text, ConflictsOut)
    if not out.candidates:
        raise ValueError("候选为空")
    return out.candidates


def gen_body(llm, conflict: str, title: str) -> BodyOut:
    system = read_prompt("body_system")
    user = json.dumps({"conflict": conflict, "title": title}, ensure_ascii=False)
    for _ in range(MAX_ATTEMPTS):
        out: BodyOut = _ask(llm, system, user, BodyOut)
        stripped = out.body.strip()
        clean_len = sum(1 for ch in stripped if "\u4e00" <= ch <= "\u9fff")
        if 20 <= clean_len <= 70:
            return BodyOut(body=stripped, mood=out.mood.strip())
    return out


def gen_image_prompt(llm, body: str, mood: str) -> str:
    user = read_prompt("image_style").format(body=body, mood=mood)
    out: ImagePromptOut = _ask(llm, "你是专业的人像摄影提示词生成器", user, ImagePromptOut)
    return out.image_prompt.strip()
```

说明：`image_style.txt` 渲染后作为该次调用的 user 消息。`gen_body` 长度校验按汉字数放宽到 20–70 以容忍标点计数差异，超长时重试、末次仍超长则原样返回交人工删减。

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_stages.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "feat: 三个生成阶段纯函数"
```

### Task 6: 一键成稿流水线 pipeline

**Files:**
- Create: `backend/app/services/pipeline.py`
- Modify: `backend/app/schemas.py`（BuildIn 增加可选 `candidates` 字段）
- Test: `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: Task 5 的三个 stage 函数；Task 1 的 ORM；Task 2 的 schemas
- Produces（后续路由层直接调用）:
  - `source_text(db, topic_id=None, idea="") -> str`
  - `draft_conflicts(db, llm, topic_id=None, idea="") -> list[Candidate]`（记日志）
  - `build_article(db, llm, ark, data: BuildIn, storage_root: Path, default_size: str, max_count: int) -> Article`
  - `generate_images(ark, article, count, storage_root: Path) -> list[str]`（返回形如 `runs/<id>/x.jpg` 的相对路径）
  - 每阶段写 `GenerationLog(stage in conflict/body/image_prompt/image)`
- BuildIn 新增：`candidates: list[Candidate] | None = None`（向导把第一步候选传回，持久化到 `title_candidates`）

- [ ] **Step 1: 在 schemas.py 的 BuildIn 中追加字段**

```python
class BuildIn(BaseModel):
    topic_id: int | None = None
    conflict: str
    title: str
    image_size: str | None = None
    image_count: int | None = None
    candidates: list[Candidate] | None = None
```

- [ ] **Step 2: 写失败测试**

`backend/tests/test_pipeline.py`：

```python
from pathlib import Path

import pytest

from app.models import GenerationLog, Topic
from app.schemas import BuildIn, Candidate
from app.services.pipeline import build_article, draft_conflicts, source_text


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.model = "fake-model"

    def chat_json(self, system, user, temperature=0.8):
        self.calls.append((system, user))
        return self.responses.pop(0)


class FakeArk:
    def __init__(self):
        self.calls = []

    def generate_image(self, prompt, size, output_path):
        self.calls.append((prompt, size))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"img")
        return output_path


@pytest.fixture
def topic(test_session):
    t = Topic(drive_type="恐惧", category="情感关系", conflict="遇不到合适的人")
    test_session.add(t)
    test_session.commit()
    return t


def make_llm():
    return FakeLLM([
        {"body": "以前总觉得来日方长，现在只想过好今天。", "mood": "黄昏阳台"},
        {"image_prompt": "candid photo of a woman at dusk"},
    ])


def test_source_text_from_topic(test_session, topic):
    text = source_text(test_session, topic_id=topic.id)
    assert "恐惧" in text and "遇不到合适的人" in text
    assert "自由想法" in source_text(test_session, idea="随便写写")


def test_draft_conflicts_logs(test_session, test_engine):
    from app.database import Base

    Base.metadata.create_all(test_engine)
    llm = FakeLLM([{"candidates": [
        {"conflict": "c", "titles": ["t1", "t2", "t3", "t4", "t5"]},
    ]}])
    out = draft_conflicts(test_session, llm, idea="x")
    assert len(out) == 1
    logs = test_session.query(GenerationLog).all()
    assert logs[0].stage == "conflict"
    assert logs[0].ok is True
    assert logs[0].model == "fake-model"


def test_build_article_full_flow(test_session, test_engine, tmp_path, topic):
    from app.database import Base

    Base.metadata.create_all(test_engine)
    llm = make_llm()
    ark = FakeArk()
    data = BuildIn(
        topic_id=topic.id,
        conflict="心动还是稳定",
        title="35岁，我选了稳定",
        image_count=2,
        candidates=[Candidate(conflict="心动还是稳定", titles=["35岁，我选了稳定"])],
    )
    article = build_article(
        test_session, llm, ark, data,
        storage_root=tmp_path / "storage",
        default_size="1080x1620", max_count=3,
    )
    assert article.body.startswith("以前总觉得")
    assert article.mood == "黄昏阳台"
    assert article.image_prompt == "candid photo of a woman at dusk"
    assert len(article.image_paths) == 2
    assert article.image_paths[0].startswith(f"runs/{article.id}/")
    saved = tmp_path / "storage" / article.image_paths[0]
    assert saved.read_bytes() == b"img"
    assert len(ark.calls) == 2
    assert ark.calls[0][1] == "1080x1620"
    stages = [l.stage for l in test_session.query(GenerationLog).all()]
    assert stages == ["body", "image_prompt", "image"]
    assert topic.use_count == 1
    assert article.title_candidates[0]["conflict"] == "心动还是稳定"


def test_build_respects_max_count(test_session, test_engine, tmp_path, topic):
    from app.database import Base

    Base.metadata.create_all(test_engine)
    ark = FakeArk()
    data = BuildIn(topic_id=topic.id, conflict="c", title="t", image_count=9)
    article = build_article(
        test_session, make_llm(), ark, data,
        storage_root=tmp_path / "storage",
        default_size="1080x1620", max_count=3,
    )
    assert len(article.image_paths) == 3
```

- [ ] **Step 3: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_pipeline.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 4: 实现 pipeline**

`backend/app/services/pipeline.py`：

```python
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Article, GenerationLog, Topic
from app.schemas import BuildIn
from app.services.stages import draft_conflicts as _stage_conflicts
from app.services.stages import gen_body, gen_image_prompt


def _model_name(llm) -> str:
    return str(getattr(llm, "model", ""))


def _log(db: Session, article_id: int | None, stage: str, llm, t0: float,
         ok: bool = True, error: str | None = None) -> None:
    db.add(GenerationLog(
        article_id=article_id,
        stage=stage,
        model=_model_name(llm),
        ok=ok,
        error=(error or None) if ok is False else None if False else error,
        elapsed_ms=int((time.time() - t0) * 1000),
    ))
    db.commit()


def source_text(db: Session, topic_id: int | None = None, idea: str = "") -> str:
    if topic_id:
        topic = db.get(Topic, topic_id)
        if not topic:
            raise ValueError("主题不存在")
        return f"驱动类型：{topic.drive_type}\n分类：{topic.category}\n素材：{topic.conflict}"
    if not idea.strip():
        raise ValueError("必须提供主题或想法")
    return f"自由想法：{idea.strip()}"


def draft_conflicts(db: Session, llm, topic_id: int | None = None, idea: str = "") -> list:
    text = source_text(db, topic_id, idea)
    t0 = time.time()
    try:
        candidates = _stage_conflicts(llm, text)
        _log(db, None, "conflict", llm, t0)
        return candidates
    except Exception as exc:
        _log(db, None, "conflict", llm, t0, ok=False, error=str(exc))
        raise


def generate_images(ark, article: Article, count: int, storage_root: Path) -> list[str]:
    folder = storage_root / "runs" / str(article.id)
    paths = []
    for i in range(count):
        fname = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}.jpg"
        ark.generate_image(article.image_prompt, article.image_size, folder / fname)
        paths.append(f"runs/{article.id}/{fname}")
    return paths


def build_article(db: Session, llm, ark, data: BuildIn, storage_root: Path,
                  default_size: str = "1080x1620", max_count: int = 3) -> Article:
    article = Article(
        topic_id=data.topic_id,
        title=data.title.strip(),
        image_size=data.image_size or default_size,
    )
    if data.candidates:
        article.title_candidates = [c.model_dump() for c in data.candidates]
    else:
        article.title_candidates = [{"conflict": data.conflict, "titles": [data.title]}]
    db.add(article)
    db.commit()
    db.refresh(article)

    t0 = time.time()
    try:
        body_out = gen_body(llm, data.conflict, article.title)
    except Exception as exc:
        _log(db, article.id, "body", llm, t0, ok=False, error=str(exc))
        raise
    article.body = body_out.body
    article.mood = body_out.mood
    _log(db, article.id, "body", llm, t0)
    db.commit()

    t0 = time.time()
    try:
        article.image_prompt = gen_image_prompt(llm, article.body, article.mood)
    except Exception as exc:
        _log(db, article.id, "image_prompt", llm, t0, ok=False, error=str(exc))
        raise
    _log(db, article.id, "image_prompt", llm, t0)
    db.commit()

    count = min(max(data.image_count or 1, 1), max_count)
    t0 = time.time()
    try:
        article.image_paths = generate_images(ark, article, count, storage_root)
    except Exception as exc:
        _log(db, article.id, "image", llm, t0, ok=False, error=str(exc))
        raise
    _log(db, article.id, "image", llm, t0)
    db.commit()

    if data.topic_id:
        topic = db.get(Topic, data.topic_id)
        if topic:
            topic.use_count += 1
            db.commit()
    return article
```

修正 `_log` 中 error 参数的冗余表达式，直接写：

```python
        error=error,
```

- [ ] **Step 5: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_pipeline.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```powershell
git add -A
git commit -m "feat: 一键成稿流水线与生成日志"
```

---

### Task 7: 局部重生与文章管理接口

**Files:**
- Create: `backend/app/routers/generation.py`, `backend/app/routers/articles.py`
- Modify: `backend/app/services/pipeline.py`（追加三个 regen 函数）, `backend/app/main.py`（挂载新路由、注入客户端）
- Test: `backend/tests/test_generation_api.py`, `backend/tests/test_articles_api.py`

**Interfaces:**
- Consumes: Task 6 全部函数；Task 3 客户端；Task 1 models
- Produces:
  - `POST /api/generation/draft-conflicts` `{topic_id?, idea}` → `{"candidates":[{conflict,titles[]}]}`
  - `POST /api/generation/build` → `ArticleOut`
  - `POST /api/articles/{id}/regen-titles|regen-body|regen-images` → `ArticleOut`
  - `GET/PATCH/DELETE /api/articles*`、`POST /api/articles/{id}/status`
  - `create_app(session_factory=None, llm=None, ark=None, storage_root="storage")`——测试注入 FakeLLM/FakeArk 与 tmp 目录
  - pipeline 追加：`get_article(db,id)`、`regen_titles/regen_body/regen_images(db,llm,ark,id,count,storage_root)`

- [ ] **Step 1: pipeline 追加重生函数（先写进实现，随后由 API 测试覆盖）**

在 `backend/app/services/pipeline.py` 末尾追加：

```python
def get_article(db: Session, article_id: int) -> Article:
    article = db.get(Article, article_id)
    if not article:
        raise ValueError(f"内容包不存在: {article_id}")
    return article


def _current_conflict(article: Article) -> str:
    for cand in article.title_candidates or []:
        if isinstance(cand, dict) and article.title in cand.get("titles", []):
            return cand.get("conflict", "")
    first = article.title_candidates[0] if article.title_candidates else {}
    return first.get("conflict", "") if isinstance(first, dict) else ""


def regen_titles(db: Session, llm, article_id: int) -> Article:
    article = get_article(db, article_id)
    src = (
        f"现有标题：{article.title}\n"
        f"冲突方向：{_current_conflict(article)}\n"
        f"正文片段：{article.body[:50]}"
    )
    t0 = time.time()
    try:
        candidates = _stage_conflicts(llm, src)
        article.title_candidates = [c.model_dump() for c in candidates]
    except Exception as exc:
        _log(db, article.id, "titles_regen", llm, t0, ok=False, error=str(exc))
        raise
    _log(db, article.id, "titles_regen", llm, t0)
    db.commit()
    db.refresh(article)
    return article


def regen_body(db: Session, llm, article_id: int) -> Article:
    article = get_article(db, article_id)
    t0 = time.time()
    try:
        out = gen_body(llm, _current_conflict(article), article.title)
        article.body = out.body
        article.mood = out.mood
    except Exception as exc:
        _log(db, article.id, "body_regen", llm, t0, ok=False, error=str(exc))
        raise
    _log(db, article.id, "body_regen", llm, t0)
    db.commit()
    db.refresh(article)
    return article


def regen_images(db: Session, ark, article_id: int, count: int,
                 storage_root: Path, max_count: int = 3) -> Article:
    article = get_article(db, article_id)
    n = min(max(count, 1), max_count)
    article.image_paths = generate_images(ark, article, n, storage_root)
    db.commit()
    db.refresh(article)
    return article
```

- [ ] **Step 2: 写 API 失败测试**

`backend/tests/test_generation_api.py`：

```python
import pytest

from app.schemas import BuildIn
from app.services.pipeline import build_article
from tests.test_pipeline import FakeArk, FakeLLM, make_llm

BUILD_BODY = {
    "topic_id": None,
    "conflict": "心动还是稳定",
    "title": "35岁，我选了稳定",
}


@pytest.fixture
def wired(client):
    llm = make_llm()
    ark = FakeArk()
    client.app.state.llm = llm
    client.app.state.ark = ark
    return client, llm, ark


def test_build_endpoint(wired):
    client, _, ark = wired
    r = client.post("/api/generation/build", json=BUILD_BODY)
    assert r.status_code == 200
    data = r.json()
    assert data["body"].startswith("以前总觉得")
    assert len(data["image_paths"]) == 1
    detail = client.get(f"/api/articles/{data['id']}")
    assert detail.status_code == 200


def test_regen_endpoints_only_touch_own_fields(wired):
    client, llm, ark = wired
    aid = client.post("/api/generation/build", json=BUILD_BODY).json()["id"]

    llm.responses.append({"candidates": [
        {"conflict": "新的冲突", "titles": ["新标题一", "新标题二", "新标题三", "新标题四", "新标题五"]},
    ]})
    r = client.post(f"/api/articles/{aid}/regen-titles")
    assert r.json()["title_candidates"][0]["titles"][0] == "新标题一"
    old_title = r.json()["title"]
    assert old_title == BUILD_BODY["title"]

    llm.responses.append({"body": "换一种说法的全新正文，字数刚好合适。", "mood": "深夜路灯"})
    r = client.post(f"/api/articles/{aid}/regen-body")
    data = r.json()
    assert data["body"].startswith("换一种说法")
    assert data["mood"] == "深夜路灯"

    r = client.post(f"/api/articles/{aid}/regen-images", json={"count": 2})
    assert len(r.json()["image_paths"]) == 2


def test_draft_conflicts_endpoint(wired):
    client, llm, _ = wired
    llm.responses.append({"candidates": [
        {"conflict": "c1", "titles": ["t1", "t2", "t3", "t4", "t5"]},
    ]})
    r = client.post("/api/generation/draft-conflicts", json={"idea": "大龄单身"})
    assert r.json()["candidates"][0]["conflict"] == "c1"
```

`backend/tests/test_articles_api.py`：

```python
import pytest

from tests.test_generation_api import BUILD_BODY, wired


def make_article(client):
    return client.post("/api/generation/build", json=BUILD_BODY).json()


def test_patch_and_status_and_list(client, wired):
    art = make_article(client)
    aid = art["id"]

    r = client.patch(f"/api/articles/{aid}", json={"body": "手工改过的正文"})
    assert r.json()["body"] == "手工改过的正文"
    assert r.json()["title"] == art["title"]

    r = client.post(f"/api/articles/{aid}/status", json={"status": "approved"})
    assert r.json()["status"] == "approved"
    r = client.post(f"/api/articles/{aid}/status", json={"status": "draft"})
    assert r.json()["status"] == "draft"

    client.post("/api/generation/build", json={**BUILD_BODY, "title": "第二篇"})
    r = client.get("/api/articles")
    assert r.json()["total"] == 2
    r = client.get("/api/articles", params={"q": "第二篇"})
    assert r.json()["total"] == 1


def test_status_validated(client, wired):
    art = make_article(client)
    r = client.post(f"/api/articles/{art['id']}/status", json={"status": "nope"})
    assert r.status_code == 422


def test_delete_removes_files(client, wired, tmp_path):
    art = make_article(client)
    aid = art["id"]
    rel = art["image_paths"][0]
    f = tmp_path / "storage" / rel
    assert f.exists()
    assert client.delete(f"/api/articles/{aid}").status_code == 204
    assert not f.exists()
    assert client.get(f"/api/articles/{aid}").status_code == 404
```

`backend/tests/conftest.py` 整体替换为最终版（占位客户端 + tmp 存储目录）：

```python
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
```

同时把 `test_delete_removes_files` 中文件断言改为：

```python
def test_delete_removes_files(client, wired):
    art = make_article(client)
    aid = art["id"]
    f = client.storage_root / art["image_paths"][0]
    assert f.exists()
    assert client.delete(f"/api/articles/{aid}").status_code == 204
    assert not f.exists()
    assert client.get(f"/api/articles/{aid}").status_code == 404
```

`tests/test_generation_api.py` 顶部导入保持 `from tests.test_pipeline import FakeArk, FakeLLM, make_llm` 不变（pytest 以 backend 为根目录运行，`tests` 是包）。

- [ ] **Step 3: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_generation_api.py tests/test_articles_api.py -v`
Expected: FAIL（404 路由不存在或 ImportError）

- [ ] **Step 4: 实现两个路由并改造 main**

`backend/app/routers/generation.py`：

```python
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
```

`backend/app/routers/articles.py`：

```python
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article
from app.schemas import ArticleListOut, ArticleOut, ArticlePatch, StatusIn
from app.services import pipeline

router = APIRouter(prefix="/api/articles", tags=["articles"])

VALID_STATUS = {"draft", "approved", "published"}


@router.get("", response_model=ArticleListOut)
def list_articles(status: str | None = None, q: str | None = None,
                  page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    query = db.query(Article)
    if status:
        query = query.filter(Article.status == status)
    if q:
        query = query.filter(Article.title.contains(q))
    total = query.count()
    items = (
        query.order_by(Article.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"total": total, "items": items}


@router.get("/{article_id}", response_model=ArticleOut)
def get_one(article_id: int, db: Session = Depends(get_db)):
    try:
        return pipeline.get_article(db, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.patch("/{article_id}", response_model=ArticleOut)
def patch_article(article_id: int, data: ArticlePatch, db: Session = Depends(get_db)):
    try:
        article = pipeline.get_article(db, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(article, k, v)
    db.commit()
    db.refresh(article)
    return article


@router.post("/{article_id}/status", response_model=ArticleOut)
def set_status(article_id: int, data: StatusIn, db: Session = Depends(get_db)):
    if data.status not in VALID_STATUS:
        raise HTTPException(422, "非法状态")
    try:
        article = pipeline.get_article(db, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    article.status = data.status
    db.commit()
    db.refresh(article)
    return article


@router.delete("/{article_id}", status_code=204)
def delete_article(article_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        article = pipeline.get_article(db, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    folder = Path(request.app.state.storage_root) / "runs" / str(article_id)
    shutil.rmtree(folder, ignore_errors=True)
    db.delete(article)
    db.commit()
```

`backend/app/main.py` 整体替换为：

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from app.clients.ark import ArkClient
from app.clients.deepseek import DeepSeekClient
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.routers import articles, generation, prompts_api, topics
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
    return app


app = create_app()
```

注意：Task 2 曾让 `test_seed_idempotent` 第二次调用默认参数 `create_app()`——现在会构造真实客户端但不会发起网络请求，安全。

- [ ] **Step 5: 运行全部后端测试确认通过**

Run: `.venv\Scripts\python -m pytest -v`
Expected: 全部通过（约 16 个）

- [ ] **Step 6: Commit**

```powershell
git add -A
git commit -m "feat: 局部重生接口与文章管理接口"
```

### Task 8: 导出功能（zip + Markdown）

**Files:**
- Create: `backend/app/services/export.py`
- Modify: `backend/app/routers/articles.py`（追加导出路由）
- Test: `backend/tests/test_export.py`

**Interfaces:**
- Consumes: `Article`；`client.storage_root`
- Produces: `build_markdown(article) -> str`；`build_zip(article, storage_root: Path) -> bytes`；`GET /api/articles/{id}/export.zip` → `application/zip` 附件下载

Markdown 格式（供复制到公众号编辑器）：

```
# {标题}

{正文}
```

zip 内结构：`article.md` + `images/<原文件名>`。

- [ ] **Step 1: 写失败测试**

`backend/tests/test_export.py`：

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_export.py -v`
Expected: FAIL（404 / ModuleNotFoundError）

- [ ] **Step 3: 实现 export 服务与路由**

`backend/app/services/export.py`：

```python
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
```

在 `backend/app/routers/articles.py` 末尾追加：

```python
from fastapi.responses import Response

from app.services.export import build_zip


@router.get("/{article_id}/export.zip")
def export_article(article_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        article = pipeline.get_article(db, article_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    content = build_zip(article, Path(request.app.state.storage_root))
    filename = f"article_{article_id}.zip"
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_export.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "feat: 内容包zip与Markdown导出"
```

---

### Task 9: 设置接口、.env 持久化与应用装配收尾

**Files:**
- Create: `backend/app/services/envfile.py`, `backend/app/routers/settings_api.py`
- Modify: `backend/app/main.py`（挂载 settings 路由、静态资源、启动脚本说明）
- Test: `backend/tests/test_settings_api.py`

**Interfaces:**
- Produces:
  - `read_env(path=".env") -> dict`、`write_env(values: dict, path=".env") -> None`（保留未知行）
  - `GET /api/settings` → `{deepseek_api_key_masked, deepseek_model, volcengine_ark_api_key_masked, volcengine_ark_image_model, image_size_default, presets, image_count_default, image_count_max, api_ready}`；`PUT /api/settings` 持久化明文 key 到 .env 并热更新 `app.state.llm/ark/default_size/max_count`
  - `GET /api/presets` → `[{label,size}]`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_settings_api.py`：

```python
def test_env_roundtrip(tmp_path):
    from app.services.envfile import read_env, write_env

    env_path = tmp_path / ".env"
    env_path.write_text(
        "A=1\nB=2\n", encoding="utf-8",
    )
    write_env({"A": "9", "C": "3"}, path=str(env_path))
    data = read_env(str(env_path))
    assert data["A"] == "9"
    assert data["B"] == "2"
    assert data["C"] == "3"


def test_get_and_put_settings(client):
    data = client.get("/api/settings").json()
    assert "presets" in data and len(data["presets"]) >= 3
    assert data["image_size_default"] == "1080x1620"
    assert "deepseek_api_key" not in data

    client.app.state.storage_root  # 触发属性存在性
    r = client.put("/api/settings", json={
        "deepseek_model": "deepseek-chat",
        "image_count_default": 2,
    })
    assert r.status_code == 200
    assert client.app.state.max_count == 3


def test_presets_endpoint(client):
    data = client.get("/api/presets").json()
    assert {"label": "2:3", "size": "1080x1620"} in data
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_settings_api.py -v`
Expected: FAIL（404 / ModuleNotFoundError）

- [ ] **Step 3: 实现 envfile 与 settings 路由**

`backend/app/services/envfile.py`：

```python
from pathlib import Path


def read_env(path: str = ".env") -> dict:
    result = {}
    p = Path(path)
    if not p.exists():
        return result
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


def write_env(values: dict, path: str = ".env") -> None:
    p = Path(path)
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    remaining = dict(values)
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.partition("=")[0].strip()
            if key in values:
                out.append(f"{key}={values[key]}")
                remaining.pop(key, None)
                continue
        out.append(line)
    for key, val in remaining.items():
        out.append(f"{key}={val}")
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
```

`backend/app/routers/settings_api.py`：

```python
import os

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.config import get_presets
from app.config import settings as cfg
from app.services.envfile import read_env, write_env

WRITABLE_KEYS = {
    "DEEPSEEK_API_KEY": "deepseek_api_key",
    "DEEPSEEK_MODEL": "deepseek_model",
    "VOLCENGINE_ARK_API_KEY": "volcengine_ark_api_key",
    "VOLCENGINE_ARK_IMAGE_MODEL": "volcengine_ark_image_model",
    "IMAGE_SIZE_DEFAULT": "image_size_default",
    "IMAGE_COUNT_DEFAULT": "image_count_default",
}

ENV_PATH = os.environ.get("WECHATGZH_ENV_FILE", ".env")

router = APIRouter(prefix="/api", tags=["settings"])


class SettingsIn(BaseModel):
    deepseek_api_key: str | None = None
    deepseek_model: str | None = None
    volcengine_ark_api_key: str | None = None
    volcengine_ark_image_model: str | None = None
    image_size_default: str | None = None
    image_count_default: int | None = None


def _mask(value: str) -> str:
    if not value:
        return ""
    return "*" * max(len(value) - 4, 0) + value[-4:]


@router.get("/presets")
def presets():
    return get_presets()


@router.get("/settings")
def get_settings():
    return {
        "deepseek_api_key_masked": _mask(cfg.deepseek_api_key),
        "deepseek_model": cfg.deepseek_model,
        "volcengine_ark_api_key_masked": _mask(cfg.volcengine_ark_api_key),
        "volcengine_ark_image_model": cfg.volcengine_ark_image_model,
        "image_size_default": cfg.image_size_default,
        "presets": get_presets(),
        "image_count_default": cfg.image_count_default,
        "image_count_max": cfg.image_count_max,
        "api_ready": bool(cfg.deepseek_api_key and cfg.volcengine_ark_api_key),
    }


@router.put("/settings")
def put_settings(data: SettingsIn, request: Request):
    incoming = data.model_dump(exclude_none=True)
    env_updates = {}
    for env_key, field in WRITABLE_KEYS.items():
        if field in incoming:
            env_updates[env_key] = str(incoming[field])
            setattr(cfg, field, incoming[field])
    if env_updates:
        write_env(env_updates, path=ENV_PATH)
    request.app.state.default_size = cfg.image_size_default
    request.app.state.max_count = cfg.image_count_max
    if cfg.deepseek_api_key and cfg.deepseek_model:
        from app.clients.deepseek import DeepSeekClient

        request.app.state.llm = DeepSeekClient(
            cfg.deepseek_base_url, cfg.deepseek_api_key, cfg.deepseek_model,
        )
    if cfg.volcengine_ark_api_key and cfg.volcengine_ark_image_model:
        from app.clients.ark import ArkClient

        request.app.state.ark = ArkClient(
            cfg.volcengine_ark_base_url, cfg.volcengine_ark_api_key,
            cfg.volcengine_ark_image_model,
        )
    return {"ok": True}
```

- [ ] **Step 4: main.py 收尾**

在 `create_app` 中：导入 `settings_api`，与其他路由一起挂载；并在函数末尾、`return app` 之前加入静态资源兜底：

```python
    static_dir = Path("static")
    if (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(html=True), name="spa")
```

顶部补 `from pathlib import Path` 与 `from fastapi.staticfiles import StaticFiles`。注意挂载必须放在所有 include_router 之后。

项目根 `.gitignore` 追加：`node_modules/`、`frontend/dist/`。

创建根目录启动脚本 `start_backend.ps1`：

```powershell
Set-Location backend
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- [ ] **Step 5: 运行全部后端测试**

Run: `.venv\Scripts\python -m pytest -v`
Expected: 全部通过（约 21 个）

- [ ] **Step 6: 手动冒烟（不调真实 API）**

Run: `.venv\Scripts\uvicorn app.main:app --port 8000` 后浏览器打开 `http://127.0.0.1:8000/docs`
Expected: Swagger 正常，`/api/topics` 返回种子数据

- [ ] **Step 7: Commit**

```powershell
git add -A
git commit -m "feat: 设置接口、env持久化与静态资源兜底"
```

### Task 10: 前端骨架与内容包首页

**Files:**
- Create: `frontend/`（Vite 脚手架）、`frontend/vite.config.js`、`frontend/index.html`(改)、`frontend/src/main.js`、`frontend/src/api.js`、`frontend/src/router.js`、`frontend/src/App.vue`、`frontend/src/views/HomeView.vue`
- Delete: 脚手架默认的 `src/components/HelloWorld.vue`、`src/style.css` 引用

**Interfaces:**
- Consumes: 后端 `/api/articles` 列表接口；静态图片路径 `/files/<image_paths[i]>`
- Produces: `api`（axios 实例，baseURL `/api`）；`fileUrl(p)` 工具；路由表 `/`,`/wizard`,`/articles/:id`,`/topics`,`/settings`；侧边栏布局

- [ ] **Step 1: 脚手架与依赖**

```powershell
npm create vite@latest frontend -- --template vue
cd frontend
npm install
npm install element-plus @element-plus/icons-vue pinia vue-router axios
```

Run: `npm run dev`
Expected: 默认页面在 5173 端口打开

- [ ] **Step 2: 配置 vite 与入口文件**

`frontend/vite.config.js` 整体替换：

```js
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/files': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: '../backend/static',
    emptyOutDir: true,
  },
})
```

`frontend/index.html` 中 `<html lang="en">` 改为 `<html lang="zh-CN">`，`<title>` 改为 `情感内容工作台`。

`frontend/src/main.js` 整体替换：

```js
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

createApp(App).use(createPinia()).use(router).use(ElementPlus, { locale: zhCn }).mount('#app')
```

删除 `frontend/src/components/HelloWorld.vue` 与 `frontend/src/style.css`，并移除 `main.js` 里对 style.css 的引用（上面整体替换已不含它）。

`frontend/src/api.js`：

```js
import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    const msg = err?.response?.data?.detail || err.message || '请求失败'
    if (window.__elMessage) window.__elMessage.error(String(msg))
    return Promise.reject(err)
  },
)

export const fileUrl = (p) => `/files/${p}`
```

`window.__elMessage` 在 main.js 里注入（放 ElementPlus 导入之后）：

```js
import { ElMessage } from 'element-plus'
window.__elMessage = ElMessage
```

`frontend/src/router.js`：

```js
import { createRouter, createWebHistory } from 'vue-router'
import DetailView from './views/DetailView.vue'
import HomeView from './views/HomeView.vue'
import SettingsView from './views/SettingsView.vue'
import TopicsView from './views/TopicsView.vue'
import WizardView from './views/WizardView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/wizard', component: WizardView },
    { path: '/articles/:id', component: DetailView },
    { path: '/topics', component: TopicsView },
    { path: '/settings', component: SettingsView },
  ],
})

export default router
```

注意：此时 DetailView/TopicsView/SettingsView 尚不存在。为让本任务可运行，先创建三个占位组件（Task 11–13 会替换）：

`frontend/src/views/DetailView.vue`：

```vue
<template><el-empty description="详情页建设中" /></template>
```

`frontend/src/views/TopicsView.vue`：

```vue
<template><el-empty description="主题库建设中" /></template>
```

`frontend/src/views/SettingsView.vue`：

```vue
<template><el-empty description="设置页建设中" /></template>
```

`frontend/src/views/WizardView.vue` 占位：

```vue
<template><el-empty description="新建向导建设中" /></template>
```

- [ ] **Step 3: 布局 App.vue 与首页**

`frontend/src/App.vue` 整体替换：

```vue
<script setup>
import { Document, FolderOpened, Menu, Setting, Star } from '@element-plus/icons-vue'
</script>

<template>
  <el-container style="height: 100vh">
    <el-aside width="200px" style="border-right: 1px solid #eee">
      <div style="padding: 18px 16px; font-weight: 600">情感内容工作台</div>
      <el-menu router :default-active="$route.path">
        <el-menu-item index="/"><el-icon><Menu /></el-icon>内容包</el-menu-item>
        <el-menu-item index="/wizard"><el-icon><Document /></el-icon>新建内容</el-menu-item>
        <el-menu-item index="/topics"><el-icon><Star /></el-icon>主题库</el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon>设置</el-menu-item>
      </el-menu>
      <div style="position:absolute;bottom:16px;left:16px;color:#999;font-size:12px">
        <el-icon><FolderOpened /></el-icon> 本地工作台 v0.1
      </div>
    </el-aside>
    <el-main style="background:#f7f8fa">
      <router-view />
    </el-main>
  </el-container>
</template>
```

`frontend/src/views/HomeView.vue` 整体替换：

```vue
<script setup>
import { ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, fileUrl } from '../api'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const status = ref('')
const q = ref('')
const loading = ref(false)

const statusText = { draft: '草稿', approved: '已通过', published: '已发布' }
const statusType = { draft: 'info', approved: 'success', published: 'warning' }

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/articles', {
      params: {
        status: status.value || undefined,
        q: q.value || undefined,
        page: page.value,
        page_size: 12,
      },
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function cover(item) {
  return item.image_paths && item.image_paths.length ? fileUrl(item.image_paths[0]) : ''
}

async function remove(item) {
  await ElMessageBox.confirm(`确定删除「${item.title}」？`, '删除', { type: 'warning' })
  await api.delete(`/articles/${item.id}`)
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div style="display:flex;gap:12px;margin-bottom:16px">
      <el-select v-model="status" placeholder="全部状态" clearable style="width:140px" @change="page=1;load()">
        <el-option label="草稿" value="draft" />
        <el-option label="已通过" value="approved" />
        <el-option label="已发布" value="published" />
      </el-select>
      <el-input v-model="q" placeholder="搜索标题" clearable style="width:220px" @keyup.enter="page=1;load()" @clear="load()" />
      <el-button type="primary" @click="page=1;load()">搜索</el-button>
      <div style="flex:1"></div>
      <el-button type="primary" @click="router.push('/wizard')">新建内容</el-button>
    </div>

    <div v-loading="loading">
      <el-empty v-if="!items.length" description="还没有内容包，点右上角新建" />
      <el-row :gutter="16">
        <el-col v-for="item in items" :key="item.id" :span="6" style="margin-bottom:16px">
          <el-card shadow="hover" :body-style="{ padding: '0px' }">
            <div style="cursor:pointer" @click="router.push(`/articles/${item.id}`)">
              <el-image :src="cover(item)" fit="cover" style="width:100%;height:220px;display:block">
                <template #error><div style="height:220px;background:#eee"></div></template>
              </el-image>
              <div style="padding:12px">
                <div style="font-weight:500;margin-bottom:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ item.title }}</div>
                <div style="display:flex;justify-content:space-between;align-items:center">
                  <el-tag :type="statusType[item.status]" size="small">{{ statusText[item.status] }}</el-tag>
                  <span style="color:#999;font-size:12px">{{ new Date(item.created_at).toLocaleString('zh-CN') }}</span>
                </div>
              </div>
            </div>
            <div style="padding:0 12px 12px;text-align:right">
              <el-button link type="danger" size="small" @click="remove(item)">删除</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-pagination
        v-model:current-page="page"
        :page-size="12"
        :total="total"
        layout="prev, pager, next"
        @current-change="load"
      />
    </div>
  </div>
</template>
```

- [ ] **Step 4: 手动验证**

后端跑起来后：`.venv\Scripts\uvicorn app.main:app --port 8000`，再 `npm run dev`
Expected: 打开 http://localhost:5173 ，侧边栏四项可切换，首页显示空态

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "feat: 前端骨架、布局与内容包首页"
```

---

### Task 11: 新建向导页

**Files:**
- Modify: `frontend/src/views/WizardView.vue`（替换占位）

**Interfaces:**
- Consumes: `/api/topics?enabled=true`、`/api/presets`、`POST /api/generation/draft-conflicts`、`POST /api/generation/build`
- Produces: 完整三步向导；成功后跳转 `/articles/{id}`

- [ ] **Step 1: 实现 WizardView**

`frontend/src/views/WizardView.vue` 整体替换：

```vue
<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'

const router = useRouter()
const step = ref(0)
const topics = ref([])
const presets = ref([])
const form = reactive({ topic_id: null, idea: '', size: '', count: 1 })
const candidates = ref([])
const sel = reactive({ c: 0, t: 0 })
const drafting = ref(false)
const building = ref(false)

const currentCandidate = computed(() => candidates.value[sel.c] || null)
const currentTitle = computed(() => currentCandidate.value?.titles[sel.t] || '')

onMounted(async () => {
  const [t, p] = await Promise.all([
    api.get('/topics', { params: { enabled: true } }),
    api.get('/presets'),
  ])
  topics.value = t.data.items
  presets.value = p.data
  form.size = p.data[0]?.size || '1080x1620'
})

async function draft() {
  if (!form.topic_id && !form.idea.trim()) {
    ElMessage.warning('请选择一个主题，或输入你的想法')
    return
  }
  drafting.value = true
  try {
    const { data } = await api.post('/generation/draft-conflicts', {
      topic_id: form.topic_id,
      idea: form.idea,
    })
    candidates.value = data.candidates
    sel.c = 0
    sel.t = 0
    step.value = 1
  } catch {
    ElMessage.error('生成冲突失败，请检查 API 配置或重试')
  } finally {
    drafting.value = false
  }
}

async function build() {
  building.value = true
  try {
    const { data } = await api.post('/generation/build', {
      topic_id: form.topic_id,
      conflict: currentCandidate.value.conflict,
      title: currentTitle.value,
      image_size: form.size,
      image_count: form.count,
      candidates: candidates.value,
    })
    router.push(`/articles/${data.id}`)
  } catch {
    ElMessage.error('成稿失败，请重试')
  } finally {
    building.value = false
  }
}
</script>

<template>
  <el-card>
    <el-steps :active="step" align-center finish-status="success" style="margin-bottom:24px">
      <el-step title="选主题" />
      <el-step title="挑冲突与标题" />
      <el-step title="成稿" />
    </el-steps>

    <div v-if="step === 0" v-loading="drafting" style="max-width:640px;margin:0 auto">
      <el-form label-width="90px">
        <el-form-item label="主题库">
          <el-select v-model="form.topic_id" placeholder="从主题库选择（可选）" clearable filterable style="width:100%">
            <el-option
              v-for="t in topics"
              :key="t.id"
              :label="`[${t.drive_type}] ${t.category} · ${t.conflict}`"
              :value="t.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="自由想法">
          <el-input v-model="form.idea" type="textarea" :rows="2" placeholder="不选主题时，直接写你想要的冲突方向" />
        </el-form-item>
        <el-form-item label="图片尺寸">
          <el-select v-model="form.size" style="width:100%">
            <el-option v-for="p in presets" :key="p.size" :label="`${p.label}（${p.size}）`" :value="p.size" />
          </el-select>
        </el-form-item>
        <el-form-item label="图片数量">
          <el-input-number v-model="form.count" :min="1" :max="3" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="drafting" @click="draft">生成冲突与标题</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div v-else-if="step === 1" v-loading="building">
      <h3>第一步：选一个冲突</h3>
      <el-radio-group v-model="sel.c" style="display:flex;flex-direction:column;gap:10px">
        <el-radio v-for="(c, i) in candidates" :key="i" :value="i" border style="margin:0;padding:12px;height:auto">
          {{ c.conflict }}
        </el-radio>
      </el-radio-group>

      <h3 style="margin-top:20px">第二步：选一个标题</h3>
      <el-radio-group v-model="sel.t" style="display:flex;flex-direction:column;gap:10px">
        <el-radio v-for="(t, i) in currentCandidate?.titles || []" :key="i" :value="i" border style="margin:0;padding:12px;height:auto">
          {{ t }}
        </el-radio>
      </el-radio-group>

      <div style="margin-top:20px;display:flex;gap:12px">
        <el-button @click="step = 0">上一步</el-button>
        <el-button type="primary" :disabled="!currentTitle" :loading="building" @click="build">
          一键成稿（正文+配图）
        </el-button>
      </div>
    </div>
  </el-card>
</template>
```

- [ ] **Step 2: 手动验证**

Expected: 三步流程可走通到「一键成稿」点击（无真实 key 时报错提示正常弹出）；返回上一步切换候选正常

- [ ] **Step 3: Commit**

```powershell
git add -A
git commit -m "feat: 新建内容三步向导"
```

### Task 12: 内容包详情工作页

**Files:**
- Modify: `frontend/src/views/DetailView.vue`（替换占位）

**Interfaces:**
- Consumes: `GET/PATCH /api/articles/{id}`、`POST .../status`、`POST .../regen-titles|regen-body|regen-images`、`/files/` 静态图、`export.zip`
- Produces: 左侧公众号预览 + 右侧编辑重生区；状态流转；复制文案与下载 zip

- [ ] **Step 1: 实现 DetailView**

`frontend/src/views/DetailView.vue` 整体替换：

```vue
<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, fileUrl } from '../api'

const route = useRoute()
const id = route.params.id
const article = ref(null)
const edit = ref({ title: '', body: '', image_prompt: '' })
const candidates = ref([])
const pickedTitle = ref('')
const regenCount = ref(1)
const busy = ref('')
const statusText = { draft: '草稿', approved: '已通过', published: '已发布' }

async function load() {
  const { data } = await api.get(`/articles/${id}`)
  article.value = data
  edit.value.title = data.title
  edit.value.body = data.body
  edit.value.image_prompt = data.image_prompt
  const flat = []
  for (const c of data.title_candidates || []) {
    for (const t of c.titles || []) flat.push({ conflict: c.conflict, title: t })
  }
  candidates.value = flat.filter((x) => x.title !== data.title)
}

async function saveField(field) {
  busy.value = `save_${field}`
  try {
    const { data } = await api.patch(`/articles/${id}`, { [field]: edit.value[field] })
    article.value = data
    if (field === 'title') {
      candidates.value = candidates.value.filter((x) => x.title !== data.title)
    }
    ElMessage.success('已保存')
  } finally {
    busy.value = ''
  }
}

async function regen(kind, payload) {
  busy.value = kind
  try {
    const url = `/articles/${id}/regen-${kind}`
    const { data } = payload ? api.post(url, payload) : await api.post(url)
    article.value = data
    if (kind === 'titles') {
      const flat = []
      for (const c of data.title_candidates || []) {
        for (const t of c.titles || []) flat.push({ conflict: c.conflict, title: t })
      }
      candidates.value = flat.filter((x) => x.title !== data.title)
      pickedTitle.value = ''
      ElMessage.success('已生成新候选，挑选后点击「采用」')
    } else if (kind === 'body') {
      edit.value.body = data.body
    }
  } catch {
    ElMessage.error('生成失败，请重试')
  } finally {
    busy.value = ''
  }
}

async function adoptTitle() {
  if (!pickedTitle.value) return
  edit.value.title = pickedTitle.value
  await saveField('title')
}

async function setStatus(status) {
  busy.value = 'status'
  try {
    const { data } = await api.post(`/articles/${id}/status`, { status })
    article.value = data
  } finally {
    busy.value = ''
  }
}

function copyText() {
  const text = `${article.value.title}\n\n${article.value.body}`
  navigator.clipboard.writeText(text).then(
    () => ElMessage.success('已复制标题与正文'),
    () => ElMessage.error('复制失败，请手动选择文本'),
  )
}

const previewImages = computed(() =>
  (article.value?.image_paths || []).map((p) => fileUrl(p)),
)

onMounted(load)
</script>

<template>
  <div v-if="article">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <el-tag :type="article.status === 'draft' ? 'info' : article.status === 'approved' ? 'success' : 'warning'">
        {{ statusText[article.status] }}
      </el-tag>
      <el-radio-group :model-value="article.status" size="small" @change="setStatus">
        <el-radio-button value="draft">草稿</el-radio-button>
        <el-radio-button value="approved">通过</el-radio-button>
        <el-radio-button value="published">已发布</el-radio-button>
      </el-radio-group>
      <div style="flex:1"></div>
      <el-button @click="copyText">复制文案</el-button>
      <a :href="`/api/articles/${id}/export.zip`">
        <el-button type="primary" plain>下载 zip</el-button>
      </a>
    </div>

    <el-row :gutter="20">
      <el-col :span="10">
        <el-card header="公众号预览">
          <div style="background:#fff;padding:16px;border-radius:6px">
            <h2 style="font-size:18px;line-height:1.5;margin:0 0 12px">{{ article.title }}</h2>
            <p style="color:#555;line-height:1.8;white-space:pre-wrap;margin:0 0 12px">{{ article.body }}</p>
            <el-image
              v-for="(src, i) in previewImages"
              :key="i"
              :src="src"
              fit="cover"
              style="width:100%;margin-bottom:8px;display:block"
              :preview-src-list="previewImages"
              :initial-index="i"
            />
            <div style="color:#999;font-size:12px;text-align:center">{{ article.mood }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card header="标题">
          <el-input v-model="edit.title" />
          <div style="margin-top:10px;display:flex;gap:10px;flex-wrap:wrap;align-items:center">
            <el-select v-model="pickedTitle" placeholder="候选标题" clearable style="flex:1;min-width:260px">
              <el-option v-for="c in candidates" :key="c.title" :label="`${c.title}（${c.conflict}）`" :value="c.title" />
            </el-select>
            <el-button @click="adoptTitle">采用</el-button>
            <el-button :loading="busy === 'titles'" @click="regen('titles')">重出候选</el-button>
            <el-button type="primary" :loading="busy === 'save_title'" @click="saveField('title')">保存标题</el-button>
          </div>
        </el-card>

        <el-card header="正文（30–60字）" style="margin-top:16px">
          <el-input v-model="edit.body" type="textarea" :rows="4" />
          <div style="margin-top:10px;display:flex;gap:10px">
            <span style="color:#999;font-size:12px;line-height:32px">当前字数：{{ edit.body.length }}</span>
            <div style="flex:1"></div>
            <el-button :loading="busy === 'body'" @click="regen('body')">重写正文</el-button>
            <el-button type="primary" :loading="busy === 'save_body'" @click="saveField('body')">保存正文</el-button>
          </div>
        </el-card>

        <el-card header="配图" style="margin-top:16px">
          <el-input v-model="edit.image_prompt" type="textarea" :rows="3" placeholder="图片提示词，可手动修改后重新生图" />
          <div style="margin-top:10px;display:flex;gap:10px;align-items:center">
            <span>数量</span>
            <el-input-number v-model="regenCount" :min="1" :max="3" />
            <el-button :loading="busy === 'images'" @click="saveField('image_prompt')">保存提示词</el-button>
            <el-button type="primary" :loading="busy === 'images'" @click="regen('images', { count: regenCount })">
              重新生图
            </el-button>
          </div>
          <el-row :gutter="8" style="margin-top:12px">
            <el-col v-for="(src, i) in previewImages" :key="i" :span="8">
              <el-image :src="src" fit="cover" style="width:100%;height:160px" />
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
```

注意 `regen` 函数中三元写法有歧义，实现时统一为：

```js
    let data
    if (payload) {
      ({ data } = await api.post(url, payload))
    } else {
      ({ data } = await api.post(url))
    }
```

- [ ] **Step 2: 手动验证**

配合后端测试注入逻辑不可行——用真实 key 跑一篇完整内容，或先用 Swagger `POST /api/generation/build` 造数据。
Expected: 详情页预览与编辑联动正常；每个重生按钮只更新对应区域；状态切换即时反映到首页筛选

- [ ] **Step 3: Commit**

```powershell
git add -A
git commit -m "feat: 内容详情编辑与重生工作页"
```

---

### Task 13: 主题库管理页与设置页

**Files:**
- Modify: `frontend/src/views/TopicsView.vue`, `frontend/src/views/SettingsView.vue`（替换占位）

**Interfaces:**
- Consumes: `/api/topics` 全套 CRUD；`GET/PUT /api/settings`；`GET/PUT /api/prompts/{name}`、`PROMPT_NAMES` 经 `/api/settings` 无暴露 → 前端硬编码三个名称列表 `['conflict_system','body_system','image_style']`
- Produces: 两页完整功能

- [ ] **Step 1: 实现 TopicsView**

`frontend/src/views/TopicsView.vue` 整体替换：

```vue
<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const items = ref([])
const driveFilter = ref('')
const dialogVisible = ref(false)
const saving = ref(false)

const DRIVE_TYPES = ['欲望', '比较', '恐惧', '窥私', '站队']
const CATEGORIES = ['情感关系', '婚姻', '女性成长', '成年人的现实', '两性关系', '年龄变化', '人生阶段']

const form = reactive({ id: null, drive_type: '欲望', category: '情感关系', conflict: '' })

async function load() {
  const { data } = await api.get('/topics', {
    params: { drive_type: driveFilter.value || undefined },
  })
  items.value = data.items
}

function openCreate() {
  Object.assign(form, { id: null, drive_type: '欲望', category: '情感关系', conflict: '' })
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, row)
  dialogVisible.value = true
}

async function save() {
  if (!form.conflict.trim()) {
    ElMessage.warning('请填写冲突描述')
    return
  }
  saving.value = true
  try {
    if (form.id) {
      await api.patch(`/topics/${form.id}`, form)
    } else {
      await api.post('/topics', form)
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function toggle(row) {
  await api.patch(`/topics/${row.id}`, { enabled: row.enabled })
}

async function remove(row) {
  await ElMessageBox.confirm(`删除该主题？`, '提示', { type: 'warning' })
  await api.delete(`/topics/${row.id}`)
  load()
}

onMounted(load)
</script>

<template>
  <el-card>
    <div style="display:flex;gap:12px;margin-bottom:14px">
      <el-select v-model="driveFilter" placeholder="全部驱动类型" clearable style="width:160px" @change="load">
        <el-option v-for="d in DRIVE_TYPES" :key="d" :label="d" :value="d" />
      </el-select>
      <div style="flex:1"></div>
      <el-button type="primary" @click="openCreate">新增主题</el-button>
    </div>

    <el-table :data="items" border>
      <el-table-column prop="drive_type" label="驱动类型" width="100" />
      <el-table-column prop="category" label="分类" width="130" />
      <el-table-column prop="conflict" label="冲突素材" min-width="300" show-overflow-tooltip />
      <el-table-column prop="use_count" label="使用次数" width="90" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch v-model="row.enabled" @change="toggle(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button link size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑主题' : '新增主题'" width="520px">
      <el-form label-width="90px">
        <el-form-item label="驱动类型">
          <el-select v-model="form.drive_type">
            <el-option v-for="d in DRIVE_TYPES" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="冲突素材">
          <el-input v-model="form.conflict" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
```

- [ ] **Step 2: 实现 SettingsView**

`frontend/src/views/SettingsView.vue` 整体替换：

```vue
<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const PROMPTS = [
  { name: 'conflict_system', label: '冲突与标题' },
  { name: 'body_system', label: '正文' },
  { name: 'image_style', label: '图片风格' },
]

const s = reactive({
  deepseek_api_key_masked: '',
  deepseek_model: '',
  volcengine_ark_api_key_masked: '',
  volcengine_ark_image_model: '',
  image_size_default: '',
  presets: [],
  image_count_default: 1,
  image_count_max: 3,
  api_ready: false,
})
const keys = reactive({ deepseek_api_key: '', volcengine_ark_api_key: '' })
const promptName = ref('body_system')
const promptContent = ref('')
const savingCfg = ref(false)
const savingPrompt = ref(false)

async function load() {
  const { data } = await api.get('/settings')
  Object.assign(s, data)
}

async function loadPrompt() {
  const { data } = await api.get(`/prompts/${promptName.value}`)
  promptContent.value = data.content
}

async function saveConfig() {
  savingCfg.value = true
  try {
    await api.put('/settings', {
      deepseek_api_key: keys.deepseek_api_key || undefined,
      deepseek_model: s.deepseek_model,
      volcengine_ark_api_key: keys.volcengine_ark_api_key || undefined,
      volcengine_ark_image_model: s.volcengine_ark_image_model,
      image_size_default: s.image_size_default,
      image_count_default: s.image_count_default,
    })
    keys.deepseek_api_key = ''
    keys.volcengine_ark_api_key = ''
    await load()
    ElMessage.success('配置已保存并生效')
  } finally {
    savingCfg.value = false
  }
}

async function savePrompt() {
  savingPrompt.value = true
  try {
    await api.put(`/prompts/${promptName.value}`, { content: promptContent.value })
    ElMessage.success('提示词已保存，立即生效')
  } finally {
    savingPrompt.value = false
  }
}

onMounted(() => {
  load()
  loadPrompt()
})
</script>

<template>
  <el-row :gutter="16">
    <el-col :span="10">
      <el-card header="API 与默认配置">
        <el-alert
          v-if="!s.api_ready"
          title="尚未配置完整的 API Key，生成功能不可用"
          type="warning"
          :closable="false"
          style="margin-bottom:14px"
        />
        <el-form label-width="150px">
          <el-form-item label="DeepSeek Key">
            <el-input v-model="keys.deepseek_api_key" type="password" :placeholder="s.deepseek_api_key_masked || '未配置'" show-password />
          </el-form-item>
          <el-form-item label="DeepSeek 模型">
            <el-input v-model="s.deepseek_model" />
          </el-form-item>
          <el-form-item label="ARK Key">
            <el-input v-model="keys.volcengine_ark_api_key" type="password" :placeholder="s.volcengine_ark_api_key_masked || '未配置'" show-password />
          </el-form-item>
          <el-form-item label="ARK 图片模型">
            <el-input v-model="s.volcengine_ark_image_model" />
          </el-form-item>
          <el-form-item label="默认图片尺寸">
            <el-select v-model="s.image_size_default" style="width:100%">
              <el-option v-for="p in s.presets" :key="p.size" :label="`${p.label}（${p.size}）`" :value="p.size" />
            </el-select>
          </el-form-item>
          <el-form-item label="默认图片数量">
            <el-input-number v-model="s.image_count_default" :min="1" :max="s.image_count_max" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="savingCfg" @click="saveConfig">保存配置</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </el-col>

    <el-col :span="14">
      <el-card header="提示词模板（修改立即生效）">
        <el-tabs v-model="promptName" @tab-change="loadPrompt">
          <el-tab-pane v-for="p in PROMPTS" :key="p.name" :label="p.label" :name="p.name" />
        </el-tabs>
        <el-input v-model="promptContent" type="textarea" :rows="20" style="margin-top:8px" />
        <el-button type="primary" :loading="savingPrompt" style="margin-top:10px" @click="savePrompt">
          保存提示词
        </el-button>
      </el-card>
    </el-col>
  </el-row>
</template>
```

- [ ] **Step 3: 手动验证**

Expected: 主题库增删改查与启停生效；设置页填入真实 key 保存后 `api_ready` 变化、向导即可成功成稿；三个提示词页签可编辑保存并在下一次生成中生效

- [ ] **Step 4: Commit**

```powershell
git add -A
git commit -m "feat: 主题库管理与设置工作台页面"
```

### Task 14: 构建集成、README 与整体验收

**Files:**
- Create: `start_backend.ps1`（Task 9 已建，确认存在）、`start_frontend.ps1`、`README.md`

**Interfaces:**
- Consumes: 全部前置任务
- Produces: 一键启动脚本；生产模式单端口访问（后端托管前端静态文件）；验收清单全绿

- [ ] **Step 1: 启动脚本**

项目根 `start_backend.ps1`（若 Task 9 已建则跳过）：

```powershell
Set-Location backend
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

项目根 `start_frontend.ps1`：

```powershell
Set-Location frontend
npm run dev
```

- [ ] **Step 2: 生产构建集成**

```powershell
cd frontend
npm run build
```

Expected: 输出到 `backend/static/`，无构建错误

Run: 重启 uvicorn 后浏览器打开 `http://127.0.0.1:8000/`
Expected: 工作台首页直接可用（单端口模式）；刷新任意子路由不 404（StaticFiles html 模式对 SPA 路由返回 index.html）

若子路由刷新 404，在 main.py 静态挂载前追加兜底路由：

```python
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        target = Path("static") / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(Path("static") / "index.html")
```

注意：该兜底路由必须在 `app.mount("/", ...)` 之前注册且二者只保留其一——优先使用本兜底路由方案，删除 StaticFiles html=True 挂载。

- [ ] **Step 3: 编写 README.md**

`README.md`：

````markdown
# 情感内容工作台

AI 驱动的微信公众号情感图文内容生产系统：一键生成「冲突选题 + 标题候选 + 第一人称短文案 + 真实感配图」，本地工作台审核修改后导出发布。

## 首次配置

1. 后端环境：
   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\pip install -e ".[dev]"
   Copy-Item .env.example .env
   ```
2. 编辑 `backend/.env` 填入：
   - `DEEPSEEK_API_KEY`（DeepSeek 平台申请）
   - `VOLCENGINE_ARK_API_KEY` 与 `VOLCENGINE_ARK_IMAGE_MODEL`（火山方舟开通图片生成模型，如 seedream 系列）
3. 前端依赖：
   ```powershell
   cd frontend
   npm install
   ```

## 日常启动

开发模式（两个终端）：
- `.\start_backend.ps1`
- `.\start_frontend.ps1`
- 访问 http://localhost:5173

生产模式（单端口）：
- 先执行 `cd frontend; npm run build`
- 再运行 `.\start_backend.ps1`
- 访问 http://127.0.0.1:8000

## 使用流程

1. 设置页：确认 API 就绪、调整默认尺寸数量、可在线微调提示词
2. 主题库：维护人性驱动选题（预置12条，可增删改）
3. 新建内容 → 选主题或写想法 → 挑冲突与标题 → 自动成稿出图
4. 详情页：预览公众号效果，改字换图重生，标记通过
5. 复制文案 / 下载 zip → 粘贴到公众号编辑器发布

## 测试

```powershell
cd backend
.venv\Scripts\python -m pytest -v
```

## 技术栈

FastAPI + SQLAlchemy(SQLite) + DeepSeek + 火山方舟 ARK；Vue3 + Element Plus。设计文档见 `docs/superpowers/specs/`。
````

- [ ] **Step 4: 整体验收清单**

逐项手动验证并在每项通过后打勾：

- [ ] `pytest -v` 全绿（约21个用例）
- [ ] 首页空态 → 新建向导三步走通 → 详情页出现标题/正文/图片
- [ ] 重出标题候选不改当前标题；采用后才更新
- [ ] 重写正文只动正文与情绪标签；重新生图只动图
- [ ] 手动改正文保存后预览同步
- [ ] 状态 draft→approved→published 可来回切换
- [ ] 复制文案得到「标题+空行+正文」；zip 内含 article.md 与 images/
- [ ] 删除内容包后列表与磁盘文件同时消失
- [ ] 主题库新增的主题出现在向导下拉中；停用的主题不出现
- [ ] 提示词改坏 JSON 约束时生成报错并有日志记录（generation_logs 表 stage 对应 ok=0）
- [ ] 断网/错 key 场景：错误提示友好，已生成部分不丢失
- [ ] 单端口生产模式下刷新 `/articles/1` 不 404

- [ ] **Step 5: 最终提交**

```powershell
git add -A
git commit -m "feat: 构建集成、启动脚本与README"
```

---

### Task 15: 情感问题库资产与项目级 skill

**Files:**
- Create: `backend/templates/question_bank.json`, `.opencode/skill/emotion-bank/SKILL.md`
- Modify: `backend/app/seed.py`（增量幂等 + 并入问题库）
- Test: 修改 `backend/tests/test_topics.py` 的种子测试

**Interfaces:**
- Produces: `question_bank.json`（10 组 × 10 问）；`ensure_seed` v2——从常量种子与 question_bank.json 双源增量插入，按 conflict 判重；topics 表新增 ≥100 行问题类主题

- [ ] **Step 1: 更新种子测试（先改测试）**

把 `backend/tests/test_topics.py` 中 `test_seed_idempotent` 替换为：

```python
def test_seed_idempotent(test_session):
    ensure_seed(test_session)
    ensure_seed(test_session)
    total = test_session.query(Topic).count()
    assert total >= 100
    conflicts = [c for (c,) in test_session.query(Topic.conflict).all()]
    assert len(conflicts) == len(set(conflicts))
```

并在该文件顶部导入处确认包含：`from app.seed import ensure_seed`。

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_topics.py -v`
Expected: FAIL（总数不足 100 或重复）

- [ ] **Step 3: 创建问题库 JSON**

`backend/templates/question_bank.json`（完整内容，一次写入）：

```json
{
  "sections": [
    {
      "name": "自我认知",
      "drive_type": "恐惧",
      "questions": [
        "你认为自己在感情中最需要的是什么？",
        "你在感情中最大的优点是什么？",
        "你的哪些行为可能会阻碍你的感情发展？",
        "你是否了解自己的情感触发点？",
        "你通常如何表达自己的爱意？",
        "在一段关系中，你最害怕失去什么？",
        "你觉得自己在感情中足够独立吗？",
        "你是否容易陷入过去的感情阴影中？",
        "你是否经常反思自己在感情中的表现？",
        "你认为自己有哪些地方需要改进以更好地维护感情？"
      ]
    },
    {
      "name": "伴侣关系",
      "drive_type": "站队",
      "questions": [
        "你和伴侣之间有哪些共同的兴趣爱好？",
        "你们之间的主要沟通方式是什么？",
        "你觉得伴侣最吸引你的地方是什么？",
        "你是否了解伴侣的价值观和人生目标？",
        "你们是否有过深入的对话，讨论彼此的未来规划？",
        "你们在争吵时通常如何解决分歧？",
        "你是否觉得伴侣尊重你的个人空间和需求？",
        "你们是否经常一起创造美好的回忆？",
        "你对伴侣的期望是否合理且明确？",
        "你是否愿意为伴侣做出改变或妥协？"
      ]
    },
    {
      "name": "信任与忠诚",
      "drive_type": "恐惧",
      "questions": [
        "你是否完全信任伴侣？",
        "你有没有发现过伴侣对你隐瞒的事情？",
        "你是否觉得伴侣在感情上对你忠诚？",
        "当伴侣与其他异性交往时，你是否会感到不安？",
        "你是否曾经怀疑过伴侣的感情？",
        "你是否愿意分享自己的秘密和隐私给伴侣？",
        "你是否相信伴侣会支持你度过困难时期？",
        "你是否觉得伴侣对你的信任是坚定的？",
        "你是否觉得伴侣在你面前是真实的自己？",
        "你是否曾经因为不信任而伤害过伴侣？"
      ]
    },
    {
      "name": "沟通与理解",
      "drive_type": "窥私",
      "questions": [
        "你是否觉得与伴侣之间的沟通顺畅无阻？",
        "你是否经常倾听伴侣的想法和感受？",
        "你是否愿意向伴侣表达自己的不满和需求？",
        "你是否觉得伴侣能够理解你的立场和观点？",
        "你们是否经常一起制定决策并共同承担责任？",
        "你是否觉得伴侣在沟通时足够坦诚和直接？",
        "你是否曾经因为沟通不畅而产生误解？",
        "你是否愿意学习新的沟通技巧来改善关系？",
        "你是否觉得伴侣在沟通时能够给予你足够的关注和支持？",
        "你是否觉得伴侣在沟通时能够保持冷静和理性？"
      ]
    },
    {
      "name": "冲突解决与处理",
      "drive_type": "站队",
      "questions": [
        "你们之间是否经常出现冲突？",
        "当发生冲突时，你们通常如何解决？",
        "你是否觉得伴侣在处理冲突时足够成熟和理智？",
        "你是否曾经因为冲动而说出伤人的话？",
        "你是否愿意为了和平而主动道歉或寻求和解？",
        "你是否觉得伴侣在处理冲突时能够保持公正和客观？",
        "你是否觉得伴侣在冲突后能够迅速恢复情绪并继续前行？",
        "你是否曾经因为无法忍受冲突而选择逃避或放弃？",
        "你是否觉得伴侣在冲突中能够给予你足够的理解和包容？",
        "你是否愿意为了改善关系而接受专业的咨询或帮助？"
      ]
    },
    {
      "name": "未来规划与承诺",
      "drive_type": "比较",
      "questions": [
        "你是否对未来充满期待并与伴侣共同规划？",
        "你是否觉得伴侣与你对未来的看法一致？",
        "你们是否已经讨论了结婚或组建家庭的计划？",
        "你是否愿意为了共同的未来而努力工作和奋斗？",
        "你是否觉得伴侣是一个可以共度余生的人？",
        "你是否觉得伴侣对你的承诺是坚定和真诚的？",
        "你是否曾经因为对未来的不确定而感到焦虑或担忧？",
        "你是否觉得伴侣在为你们的未来付出努力？",
        "你是否愿意为了伴侣而放弃一些个人的梦想和目标？",
        "你是否觉得伴侣在你们的未来规划中扮演了积极的角色？"
      ]
    },
    {
      "name": "爱情观与价值观",
      "drive_type": "站队",
      "questions": [
        "你对爱情的看法是什么？",
        "你是否觉得爱情是生活中最重要的一部分？",
        "你是否愿意为了爱情而牺牲某些物质利益？",
        "你是否觉得伴侣的爱情观与你相符？",
        "你是否觉得爱情应该建立在互相尊重和理解的基础上？",
        "你是否觉得爱情需要经历考验才能更加坚固？",
        "你是相信一见钟情还是更倾向于日久生情？",
        "你是否觉得爱情需要不断经营和维护？",
        "你是否觉得伴侣对你的爱是真挚和无私的？",
        "你是否愿意为了爱情而改变自己的某些习惯或观念？"
      ]
    },
    {
      "name": "家庭与朋友的影响",
      "drive_type": "比较",
      "questions": [
        "你的家人对你们的感情有何看法？",
        "你是否觉得家人的意见对你们的感情有影响？",
        "你们是否与对方的家人建立了良好的关系？",
        "你是否觉得朋友对你们的感情持支持态度？",
        "你是否觉得朋友的建议对你们的感情有帮助？",
        "你们是否经常一起参加家庭聚会或活动？",
        "你是否觉得伴侣与你的家人相处融洽？",
        "你是否觉得伴侣的朋友对你的感情有影响？",
        "你是否愿意为了伴侣而与某些朋友保持距离？",
        "你是否觉得伴侣在处理家庭和朋友关系时足够成熟和理智？"
      ]
    },
    {
      "name": "个人成长与变化",
      "drive_type": "欲望",
      "questions": [
        "你是否觉得自己在感情中成长了许多？",
        "你是否觉得伴侣也在不断地成长和进步？",
        "你们是否一起经历了许多挑战并从中获得了力量？",
        "你是否觉得伴侣在帮助你成为更好的人方面发挥了重要作用？",
        "你是否愿意为了个人成长而接受新的挑战和机遇？",
        "你是否觉得伴侣在追求个人梦想和目标时给予了足够的支持和鼓励？",
        "你是否觉得伴侣在帮助你克服困难和挫折方面发挥了积极作用？",
        "你是否觉得伴侣在推动你走出舒适区方面起到了关键作用？",
        "你是否觉得伴侣在促进你个人成长和发展方面做出了贡献？",
        "你是否愿意为了伴侣的成长而共同努力和学习新知识？"
      ]
    },
    {
      "name": "分手与复合",
      "drive_type": "窥私",
      "questions": [
        "你是否曾经经历过分手的痛苦？",
        "你是否觉得分手是因为无法解决的分歧或矛盾？",
        "你是否曾经试图挽回一段已经结束的感情？",
        "你是否觉得复合后的感情更加珍贵和牢固？",
        "你是否觉得分手是一种解脱还是一种遗憾？",
        "你是否愿意为了复合而付出努力和代价？",
        "你是否觉得伴侣也愿意为了复合而努力？",
        "你是否觉得分手后还能做朋友？",
        "你是否觉得分手的经历让你学会了更多关于爱情和人生的道理？",
        "你是否觉得即使分手了也能从中汲取教训并为未来的感情做好准备？"
      ]
    }
  ]
}
```

- [ ] **Step 4: 创建项目级 skill**

`.opencode/skill/emotion-bank/SKILL.md`：

```markdown
---
name: emotion-bank
description: 情感选题灵感库。为本项目生成公众号情感内容选题、冲突或文案时使用；从 100 个结构化情感问题中取材并结合人性驱动类型展开。
---

# 情感选题灵感库

灵感源文件：`backend/templates/question_bank.json`

使用方法：

1. 读取该 JSON，得到 10 个分类 × 各 10 个问题的结构
2. 每个分类已映射人性驱动类型（欲望/比较/恐惧/窥私/站队）
3. 生成选题时：
   - 从未使用的问题中挑选（查询 topics 表中未被 articles 关联的记录）
   - 把问题转写为一个「年龄/身份 + 个人状态 + 冲突疑问」式标题
   - 冲突要具体、有画面感，避免说教
4. 该库同时被后端 `ensure_seed` 自动并入 topics 表；人工新增主题请走工作台主题库页面

注意：不要凭空编造问题库里没有方向的主题；如需扩展，先向用户确认再追加到 JSON。
```

- [ ] **Step 5: 实现 seed v2**

`backend/app/seed.py` 整体替换：

```python
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Topic

SEED_TOPICS = [
    ("欲望", "情感关系", "越成熟的女人越有魅力，是被生活打磨出来的"),
    ("比较", "年龄变化", "同龄人都结婚生子了，我还在等什么"),
    ("恐惧", "情感关系", "如果一直遇不到合适的人，该怎么办"),
    ("窥私", "婚姻", "一个40岁的女人离婚后，过得好吗"),
    ("站队", "婚姻", "婚姻应该选择爱情，还是稳定"),
    ("比较", "女性成长", "月薪五万以后，为什么还是不快乐"),
    ("恐惧", "年龄变化", "35岁以后，是不是就没有资格挑了"),
    ("欲望", "两性关系", "被选择和主动选择，哪个更让人安心"),
    ("窥私", "成年人的现实", "那些嫁得好的女生，后来都怎么样了"),
    ("站队", "情感关系", "心动和稳定，只能选一个"),
    ("比较", "人生阶段", "38岁还单身，真的比结婚晚了吗"),
    ("恐惧", "成年人的现实", "存款和安全感，到底哪个先来"),
]

BANK_PATH = Path("templates") / "question_bank.json"


def _bank_rows() -> list[tuple[str, str, str]]:
    if not BANK_PATH.exists():
        return []
    data = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    rows = []
    for section in data.get("sections", []):
        for question in section.get("questions", []):
            rows.append((section["drive_type"], section["name"], question))
    return rows


def ensure_seed(session: Session) -> None:
    existing = {c for (c,) in session.query(Topic.conflict).all()}
    added = False
    for drive_type, category, conflict in [*SEED_TOPICS, *_bank_rows()]:
        if conflict in existing:
            continue
        session.add(Topic(drive_type=drive_type, category=category, conflict=conflict))
        existing.add(conflict)
        added = True
    if added:
        session.commit()
```

- [ ] **Step 6: 运行测试确认通过**

Run: `.venv\Scripts\python -m pytest tests/test_topics.py -v`
Expected: 全部通过（含 ≥100 且无重复断言）

- [ ] **Step 7: Commit**

```powershell
git add -A
git commit -m "feat: 情感问题库100问资产化与增量种子"
```

---

### Task 16: 全自动选题端点与去重闭环（后端）

**Files:**
- Create: 无新文件
- Modify: `backend/app/services/pipeline.py`（追加 pick_unused_topic / auto_generate）、`backend/app/routers/generation.py`（追加 auto 端点）
- Test: `backend/tests/test_auto_api.py`

**Interfaces:**
- Consumes: Task 6 pipeline、Task 7 路由模式、Task 15 问题库主题
- Produces:
  - `pick_unused_topic(db) -> Topic | None`：启用且未被任何 Article.topic_id 关联的主题中随机一个
  - `auto_generate(db, llm, ark, storage_root, default_size, max_count) -> Article`：选 题 → 冲突标题（取首候选）→ 正文 → 配图 → 入库
  - `POST /api/generation/auto?count=N` → `{"articles": [ArticleOut...], "errors": []}`，N∈[1,5]，题库用尽时 errors 收录说明并停止

- [ ] **Step 1: 写失败测试**

`backend/tests/test_auto_api.py`：

```python
import pytest
from sqlalchemy.orm import sessionmaker

from tests.test_pipeline import FakeArk, FakeLLM


def bank_llm(n):
    responses = []
    for _ in range(n):
        responses += [
            {"candidates": [{"conflict": "自动冲突", "titles": ["自动标题一", "t2", "t3", "t4", "t5"]}]},
            {"body": "全自动生成的正文内容大概三十个字左右了", "mood": "清晨厨房"},
            {"image_prompt": "auto candid photo"},
        ]
    return FakeLLM(responses)


def test_auto_creates_distinct_articles(client):
    client.app.state.llm = bank_llm(2)
    client.app.state.ark = FakeArk()
    r = client.post("/api/generation/auto?count=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["articles"]) == 2
    assert len({a["topic_id"] for a in body["articles"]}) == 2
    assert all(a["title"] == "自动标题一" for a in body["articles"])


def test_auto_exhaustion(test_engine, tmp_path):
    from fastapi.testclient import TestClient

    from app.database import Base
    from app.main import create_app
    from app.models import Topic
    from app.services.pipeline import auto_generate

    Base.metadata.create_all(test_engine)
    Session = sessionmaker(bind=test_engine, autoflush=False)
    create_app(
        session_factory=Session,
        db_engine=test_engine,
        storage_root=str(tmp_path / "storage"),
    )

    db = Session()
    db.add(Topic(drive_type="欲望", category="x", conflict="唯一的问题"))
    db.commit()

    def make_llm():
        return FakeLLM([
            {"candidates": [{"conflict": "c", "titles": ["t1", "t2", "t3", "t4", "t5"]}]},
            {"body": "正文内容字数大概在合适范围之内了", "mood": "m"},
            {"image_prompt": "p"},
        ])

    art = auto_generate(db, make_llm(), FakeArk(), tmp_path / "storage", "1080x1620", 3)
    assert art.topic_id is not None
    with pytest.raises(ValueError, match="已全部使用"):
        auto_generate(db, make_llm(), FakeArk(), tmp_path / "storage", "1080x1620", 3)
    db.close()
```

说明：每生成一篇消耗 3 条 LLM 响应，`bank_llm(n)` 按 n 篇预置；`test_auto_exhaustion` 用单主题小库确定性验证去重与耗尽报错。

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python -m pytest tests/test_auto_api.py -v`
Expected: FAIL（ImportError: auto_generate）

- [ ] **Step 3: 实现 pipeline 追加函数**

`backend/app/services/pipeline.py` 顶部导入区补充：

```python
import random

from sqlalchemy import func
```

末尾追加：

```python
def pick_unused_topic(db: Session) -> Topic | None:
    used_ids = db.query(Article.topic_id).filter(Article.topic_id.isnot(None))
    return (
        db.query(Topic)
        .filter(Topic.enabled.is_(True), ~Topic.id.in_(used_ids))
        .order_by(func.random())
        .first()
    )


def auto_generate(db: Session, llm, ark, storage_root: Path,
                  default_size: str, max_count: int) -> Article:
    topic = pick_unused_topic(db)
    if topic is None:
        raise ValueError("题库中的问题已全部使用")
    candidates = draft_conflicts(db, llm, topic_id=topic.id)
    first = candidates[0]
    data = BuildIn(
        topic_id=topic.id,
        conflict=first.conflict,
        title=first.titles[0],
        image_size=default_size,
        image_count=1,
        candidates=candidates,
    )
    return build_article(
        db, llm, ark, data,
        storage_root=storage_root,
        default_size=default_size,
        max_count=max_count,
    )
```

- [ ] **Step 4: 实现 auto 路由**

`backend/app/routers/generation.py` 末尾追加：

```python
@router.post("/generation/auto")
def api_auto(request: Request, count: int = 1, db: Session = Depends(get_db)):
    n = min(max(count, 1), 5)
    articles = []
    errors = []
    for _ in range(n):
        try:
            article = pipeline.auto_generate(
                db, request.app.state.llm, request.app.state.ark,
                storage_root=request.app.state.storage_root,
                default_size=request.app.state.default_size,
                max_count=request.app.state.max_count,
            )
            articles.append(ArticleOut.model_validate(article))
        except ValueError as exc:
            errors.append(str(exc))
            break
        except Exception as exc:
            errors.append(f"生成失败: {exc}")
    if not articles and errors:
        raise HTTPException(400, errors[0])
    return {"articles": articles, "errors": errors}
```

- [ ] **Step 5: 运行全部后端测试**

Run: `.venv\Scripts\python -m pytest -v`
Expected: 全部通过

- [ ] **Step 6: Commit**

```powershell
git add -A
git commit -m "feat: 全自动选题端点与已用主题去重"
```

---

### Task 17: 前端「AI 全自动」入口与验收补充

**Files:**
- Modify: `frontend/src/views/HomeView.vue`
- Modify: `README.md` 使用流程、Task 14 验收清单执行时同步本节条目

**Interfaces:**
- Consumes: `POST /api/generation/auto?count=N`
- Produces: 首页一键批量生成待审内容；人工仅审核

- [ ] **Step 1: HomeView 增加 autoGenerate**

`frontend/src/views/HomeView.vue` `<script setup>` 中追加（ElMessageBox 已导入）：

```js
async function autoGenerate() {
  try {
    const { value } = await ElMessageBox.prompt('本次让 AI 自动生成几篇？（1–5）', 'AI 全自动', {
      inputValue: '1',
      inputPattern: /^[1-5]$/,
      inputErrorMessage: '请输入 1 到 5 的数字',
      confirmButtonText: '开始生成',
    })
    loading.value = true
    const { data } = await api.post('/generation/auto', null, { params: { count: Number(value) } })
    ElMessage.success(`已生成 ${data.articles.length} 篇，请到列表逐篇审核`)
    load()
  } catch (err) {
    if (err !== 'cancel' && err?.message !== 'cancel') load()
  } finally {
    loading.value = false
  }
}
```

模板工具栏「新建内容」按钮旁追加：

```html
<el-button type="success" @click="autoGenerate">AI 全自动</el-button>
```

- [ ] **Step 2: README 使用流程更新**

将 README「使用流程」第 1–2 步之间插入一行：

```markdown
2. （推荐）首页点「AI 全自动」输入篇数，AI 自动从未用过的问题里选题成稿；也可走「新建内容」手动指定主题
```

原第 2 步及以后序号顺延。

- [ ] **Step 3: 手动验证（真实 key）**

Expected:
- 点「AI 全自动」生成 2 篇 → 两篇对应不同主题；再点生成不会出现相同主题
- 把某篇删除后再次全自动 → 该主题可重新出现
- 全部主题用尽时提示「题库中的问题已全部使用」

- [ ] **Step 4: 验收清单增补（并入 Task 14 清单一起勾选）**

- [ ] 连续两次全自动生成的文章 topic_id 不同
- [ ] 已生成过内容包的主题不再被自动选中
- [ ] 删除内容包后其主题恢复可选
- [ ] 题库耗尽时返回明确错误且前端有提示
- [ ] question_bank.json 100 问全部出现在主题库页面（按分类筛选可见）

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "feat: 首页AI全自动入口与验收增补"
```

---

## 计划完成定义

以上 17 个任务全部完成并通过验收清单，即达成第一期 MVP（含 v1.1 全自动选题）：本地可视化工作台完成「AI 自动选题→成稿→配图→人工审核→导出」闭环，已使用的问题不重复。后续迭代方向（不在本计划内）：公众号草稿箱 API 对接、数据反馈系统。







