# 微信公众号情感内容生产工作台 · 设计文档

日期：2026-08-23
状态：已确认

## 一、项目目标

打造一个 AI 驱动的情感图文内容生产系统，自动生成适合微信公众号贴图形式的内容：

- 1 张（可配置 1–3 张）真实感成熟女性生活照
- 具有情绪冲突的标题（含候选）
- 第一人称情感正文

核心公式：视觉吸引 + 第一人称故事 + 人性冲突。通过本地可视化工作台完成「生成 → 审核修改 → 导出发布」闭环。

## 二、第一期范围

**做：**

- 主题库管理（增删改查、启用停用、使用次数统计）
- 一键成稿：主题 → 情感冲突 → 标题候选 → 第一人称正文 → 图片 prompt → 文生图
- 局部重生：标题、正文、图片每个环节可独立重跑；正文/图片 prompt 可手动编辑
- 内容包管理：列表、详情、状态流转（草稿/已通过/已发布）、删除、搜索
- 公众号排版预览与导出（复制文本 / 下载 zip：article.md + 图片）
- 提示词模板在线查看与编辑，保存即生效
- 设置页：API key、生成数量、图片尺寸

**不做（后期迭代）：**

- 微信公众号草稿箱/发布 API 对接
- 评论数据抓取与数据反馈系统
- 结尾讨论问题自动生成（用户明确去掉）
- AI 生成内容声明标注（用户明确去掉）

## 三、技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 后端 | Python 3.11 + FastAPI + SQLAlchemy + SQLite | 单机单文件数据库 |
| LLM | DeepSeek（chat/completions，JSON mode） | 客户端改造自 Poetry 项目 `clients/deepseek.py` |
| 文生图 | 火山引擎 ARK images/generations | 客户端改造自 Poetry 项目 `clients/volcengine_ark.py` |
| 前端 | Vue 3 + Vite + Element Plus + Pinia | CRUD 工作台组件齐全 |
| 重试 | tenacity | 与 Poetry 一致 |
| 测试 | pytest | mock httpx，不调真实 API |

项目为独立仓库 `E:\vscodeprojects\wechatgzh`，不依赖 Poetry 项目代码，仅复制改造其客户端模式。

## 四、目录结构

```
wechatgzh/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口，生产模式下挂载前端静态文件
│   │   ├── config.py        # pydantic-settings 读 .env
│   │   ├── database.py      # SQLite 引擎与 session
│   │   ├── models.py        # ORM：Topic / Article / GenerationLog
│   │   ├── schemas.py       # Pydantic 请求/响应模型
│   │   ├── routers/
│   │   │   ├── topics.py    # 主题库 CRUD
│   │   │   ├── articles.py  # 内容包 CRUD / 状态流转 / 导出
│   │   │   └── generation.py# 一键成稿 / 局部重生
│   │   ├── services/
│   │   │   ├── pipeline.py  # 一键成稿编排
│   │   │   ├── stages.py    # 单环节生成逻辑
│   │   │   └── export.py    # Markdown/zip 导出
│   │   └── clients/
│   │       ├── deepseek.py
│   │       └── ark.py
│   ├── templates/prompts/   # 外置提示词 txt
│   ├── data/app.db          # SQLite（gitignore）
│   └── storage/runs/<article_id>/  # 图片产物（gitignore）
├── frontend/                # Vue3 + Vite
├── .env.example
└── README.md
```

## 五、数据模型

### topics 主题库

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| drive_type | str | 人性驱动类型：欲望/比较/恐惧/窥私/站队 |
| category | str | 主题分类：情感关系/婚姻/女性成长/成年人的现实/两性关系 |
| conflict | text | 冲突描述（选题素材） |
| enabled | bool | 启用状态 |
| use_count | int | 被引用次数 |

预置种子数据：覆盖用户文档中全部五大驱动类型与主题分类。

### articles 内容包

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| topic_id | int FK | 关联主题，可空（手输想法） |
| title | str | 当前采用标题 |
| title_candidates | JSON | 标题候选列表（含冲突描述） |
| body | text | 第一人称正文 |
| mood | str | 情绪标签（驱动图片风格） |
| image_prompt | text | 当前图片 prompt |
| image_paths | JSON | 图片相对路径列表 |
| status | str | draft / approved / published；手动流转，允许任意回退 |
| created_at / updated_at | datetime | |

字段单独存列，局部重生只更新对应列。

### generation_logs 生成记录

id、article_id（可空，成稿前也记录）、stage（conflict/titles/body/image_prompt/image）、model、prompt 摘要、耗时 ms、成功与否、错误信息、created_at。

## 六、生成流水线

### 一键成稿（两个接口配合）

输入：`topic_id` 或自由输入想法；输出：新内容包 id。

1. 取主题冲突素材（或用户手输想法）
2. **LLM 调用①**（`POST /api/generation/draft-conflicts`）：生成结构化 JSON——3 个情感冲突候选 × 各 5 个标题候选。前端向导展示供挑选，默认取第一个
3. **LLM 调用②**（`POST /api/generation/build` 入口）：按选定冲突+标题生成第一人称正文。提示词约束：过去→变化→矛盾→困惑结构、第一人称真人口吻、有矛盾有留白、不像鸡汤；**长度 30–60 字**，短文案形态，适配贴图展示
4. **LLM 调用③**：根据正文情绪生成图片 prompt（真实感、手机摄影感、生活化、自然光、有故事感；负面约束：明星写真、网红脸、过度精修）
5. **ARK 文生图**：默认 1 张 2:3 竖版长图 1080×1620，数量可配置 1–3；尺寸为预设可配置项：`2:3(1080×1620)` / `1:1(1080×1080)` / `3:4(750×1000)` / `16:9(1920×1080)` / `9:16(1080×1920)`，新建向导中可切换，存入 storage/runs/<article_id>/
6. 写库，状态 `draft`，跳转详情页

### 局部重生（独立接口）

- `POST /api/articles/{id}/regen-titles`：重出候选，不改当前标题直到用户选用
- `POST /api/articles/{id}/regen-body`
- `POST /api/articles/{id}/regen-image`：使用现有或用户改过的 image_prompt
- `PATCH /api/articles/{id}`：手动保存标题/正文/图片 prompt 编辑

每次重生只更新对应字段并写 generation_log，其余字段不动。

### 提示词模板

`backend/templates/prompts/`：

- `conflict_system.txt` — 冲突+标题生成系统提示词
- `body_system.txt` — 正文生成系统提示词
- `image_style.txt` — 图片风格基础模板（与情绪变量拼接）

设置页可在线编辑，保存即生效（每次调用现读文件），无需重启。

## 七、API 概览

```
GET/POST/PATCH/DELETE  /api/topics
POST                   /api/articles/generate        一键成稿（步骤②后可中断选标题）
GET                    /api/articles                  列表（分页/筛选/搜索）
GET/PATCH/DELETE       /api/articles/{id}
POST                   /api/articles/{id}/regen-titles | regen-body | regen-image
POST                   /api/articles/{id}/status      状态流转
GET                    /api/articles/{id}/export.zip  导出包
GET                    /api/settings  PUT /api/settings
GET/PUT                /api/prompts/{name}            提示词读写
```

## 八、前端页面（5 个）

1. **首页/内容包列表**：卡片流，封面缩略图+标题+主题+状态标签+时间；搜索、状态筛选、删除
2. **新建向导**：选主题/手输想法 → 一键生成 → 冲突与标题候选挑选 → 自动完成剩余环节 → 跳转详情
3. **内容包详情**：左侧实时公众号预览（真实比例），右侧编辑区（标题切换候选、正文编辑、图片 prompt 编辑、各字段重生按钮）；顶部状态流转按钮
4. **主题库管理**：按驱动类型分组表格，增删改查、启停开关、使用次数
5. **设置**：API key、模型名、生成图数、尺寸、提示词在线编辑

## 九、错误处理

- LLM 返回非法 JSON：tenacity 重试 2 次（间隔 1s）→ 仍失败则该环节标记失败，保留已生成内容，前端显示重试按钮
- 文生图失败：同上，不影响文字部分
- 所有生成操作有 loading 态与耗时显示
- API key 未配置：新建向导直接引导跳转设置页
- 前端统一 axios 拦截器处理非 200 响应（Element Plus Message 提示）

## 十、测试策略

- pytest 单测：stages 的 prompt 组装与响应解析（mock httpx）、pipeline 字段更新隔离性（重生只动单字段）、export 打包、状态机合法性
- clients 通过构造注入 httpx，测试不触网
- 前端不写自动化测试，人工验收

## 十一、环境配置（.env）

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
DATA_DIR=data
STORAGE_DIR=storage/runs
```

## 十二、里程碑顺序

1. 后端骨架 + 数据模型 + 主题库 CRUD
2. DeepSeek/ARK 客户端 + 三段提示词模板
3. 一键成稿 + 局部重生流水线
4. 前端五个页面
5. 导出功能 + 联调验收

## 十三、v1.1 增补：全自动选题与问题库（2026-08-23 追加）

用户提供 100 个情感问题（分 10 类，每类 10 问），要求 AI 全面接管选题，人工只做最终审核，且不允许重复发布。

### 需求

1. **问题库资产化**
   - 100 问结构化存入 `backend/templates/question_bank.json`：`{"sections":[{"name":"自我认知","drive_type":"恐惧","questions":[...10问]}]}`
   - 分类到人性驱动类型的映射：自我认知→恐惧、伴侣关系→站队、信任与忠诚→恐惧、沟通与理解→窥私、冲突解决→站队、未来规划→比较、爱情观价值观→站队、家庭朋友→比较、个人成长→欲望、分手复合→窥私
   - 项目级 skill：`.opencode/skill/emotion-bank/SKILL.md`，说明该灵感库的位置与用法，Agent 会话可直接引用
2. **种子并入主题库**
   - `ensure_seed` 改为增量幂等：按 `conflict` 文本判重，把问题库条目并入 topics 表（category=分类名，conflict=问题原文），原有 12 条种子保留
3. **全自动选题端点**
   - `POST /api/generation/auto?count=N`（N 默认 1，上限 5）：服务端从未被任何内容包使用的启用主题中随机取一个 → LLM 展开冲突与标题（取第一个候选）→ 正文 → 配图 → 入库，循环 N 次；部分失败不中断，返回 `{articles:[], errors:[]}`
   - 无可用问题时返回错误信息「题库中的问题已全部使用」
4. **去重规则**
   - 自动选题排除条件：`topic.id IN (SELECT topic_id FROM articles WHERE topic_id IS NOT NULL)`，即只要产生过内容包（草稿/通过/已发布）就不再选中；删除内容包后该问题重新可用
   - 已发布的内容天然满足不可重复（其问题已被排除）
5. **前端入口**
   - 内容包首页工具栏增加「AI 全自动」按钮：弹窗输入生成篇数（1–5），完成后刷新列表；人工仅进入详情页审核

## 十四、v1.3 增补：端口与一键 EXE（2026-08-23 追加）

1. **后端端口 8000 → 8787**：.env.example、config 默认值、start_backend.ps1、前端 dev 代理、README 同步修改
2. **一键 EXE**：`build_exe.ps1` → PyInstaller onedir 产物 `backend/dist/GzhWorkbench/`
   - 入口 `backend/run_app.py`：冻结模式把 CWD 锚定到 exe 目录；首启从 _internal 释放 templates/static；1.5s 后自动打开浏览器 `http://127.0.0.1:8787`
   - 数据持久化在 exe 同级：data/(SQLite)、storage/(图片)、templates/prompts/(可编辑提示词)、.env
   - 分发方式：整个 GzhWorkbench 文件夹打包发送

## 十五、v2 重构：创意总监模式（2026-08-23 追加）

用户澄清核心愿景：问题库是给大模型看的「技能材料」，全部创意决策由模型完成；人只点一个按钮、最后审稿。原 SQL 抽题 + 分环节模板的模式偏离此愿景，重构如下。

### 核心流程

```
首页「一键创作」→ POST /api/creation/one-shot（每次1篇）
1. 组装材料：question_bank.json 全文注入 + 已用问题清单
2. 一次 DeepSeek 大调用（creator_system.txt = 模型的运行时技能）：
   自选未用问题 → 冲突角度 → 3个标题候选 → 30–60字第一人称正文 → 情绪标签 → 完整英文摄影提示词
3. 硬校验：所选问题必须在库内且未被占用；违规带纠偏信息重试一次，仍违规报错
4. ARK 生图 = 模型提示词原文 + 固定真实感摄影兜底后缀（自然光/胶片质感），1张
5. 入库 status=draft（含 question_text 占用标记）→ 前端直接跳详情页人工审查
```

### 取舍清单

| 处置 | 对象 |
|---|---|
| 删除 | 三步向导页、主题库管理页、「新建内容」菜单、`draft-conflicts`/`build`/`auto` 端点、`regen-titles` 端点及按钮、conflict_system/image_style 模板、SQL 抽题逻辑 |
| 新增 | `creator_system.txt` 技能提示词、`POST /api/creation/one-shot`、Article.question_text 占用字段、BuildIn.image_prompt 直通 |
| 保留 | 首页列表、详情工作页（编辑/重写正文/重新生图/状态/导出）、设置页（提示词编辑改为：创意总监提示词 + 问题库100问 两项）、gen_body（服务重写正文） |
| 调整 | question_bank.json 移入 templates/prompts/ 由白名单读写管理；seed 回退为 12 条种子不再注入题库 |

### 去重规则

用过即占用：question_text 非空的文章存在期间该问题不可再选；删除文章释放；发布过的天然永不重复。每次创作把已用清单传给模型令其避开，代码层硬校验兜底。

