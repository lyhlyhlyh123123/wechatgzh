$ErrorActionPreference = "Stop"
Set-Location frontend
npm run build
Set-Location ..\backend
.\.venv\Scripts\pip install pyinstaller --quiet
.\.venv\Scripts\pyinstaller --noconfirm --clean --name GzhWorkbench --onedir run_app.py --add-data "templates;templates" --add-data "static;static"
Write-Host ""
Write-Host "构建完成: backend\dist\GzhWorkbench\GzhWorkbench.exe"
Write-Host "使用: 把整个 GzhWorkbench 文件夹拷到任意位置，双击 GzhWorkbench.exe 即可（数据/提示词/图片保存在 exe 同级目录）。"
