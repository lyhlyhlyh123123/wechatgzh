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

说明：测试套件运行时会自动设置 `WECHATGZH_AUTO_CREATE=0`，该环境变量仅对 pytest 生效；日常用 uvicorn 启动无需任何额外操作。

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
