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
- 访问 http://127.0.0.1:8787

## 一键启动 EXE

```powershell
.\build_exe.ps1
```

产物：`backend\dist\GzhWorkbench\GzhWorkbench.exe`（文件夹版）。

- 双击运行：自动启动服务并打开浏览器（端口 8787）
- 数据全部保存在 exe 同级目录：`data\`(SQLite)、`storage\`(图片)、`templates\prompts\`(可编辑提示词)、`.env`(配置)
- 首次运行会自动释放内置模板与页面；把整个 GzhWorkbench 文件夹压缩后即可分发
- API Key 建议直接在工作台设置页填写，会写入 exe 同级的 `.env`

说明：测试套件运行时会自动设置 `WECHATGZH_AUTO_CREATE=0`，该环境变量仅对 pytest 生效；日常用 uvicorn 启动无需任何额外操作。

## 使用流程

1. 设置页：填入 DeepSeek Key 与火山 ARK Key / 图片模型；也可在线微调「创意总监提示词」与「问题库100问」
2. 首页点「一键创作」→ AI 自主选题并一次成稿配图 → 自动跳转详情页
3. 详情页审查：改标题/正文/图、重写正文、重新生图 → 标记通过
4. 复制文案 / 下载 zip → 粘贴到公众号编辑器发布
5. 已用过的问题自动占用不重复；删除文章可释放该问题

## 测试

```powershell
cd backend
.venv\Scripts\python -m pytest -v
```

## 技术栈

FastAPI + SQLAlchemy(SQLite) + DeepSeek + 火山方舟 ARK；Vue3 + Element Plus。设计文档见 `docs/superpowers/specs/`。
