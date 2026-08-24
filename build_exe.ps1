$ErrorActionPreference = "Stop"
Set-Location frontend
npm run build
Set-Location ..\backend

$appDir = Join-Path (Get-Location) "dist\GzhWorkbench"
$backup = Join-Path $env:TEMP "gzh_runtime_backup"

$hasOld = Test-Path $appDir
if ($hasOld) {
    Remove-Item $backup -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force $backup | Out-Null
    foreach ($n in @(".env", "data", "storage")) {
        if (Test-Path (Join-Path $appDir $n)) {
            Copy-Item (Join-Path $appDir $n) (Join-Path $backup $n) -Recurse -Force
        }
    }
    New-Item -ItemType Directory -Force (Join-Path $backup "templates_prompts") | Out-Null
    if (Test-Path (Join-Path $appDir "templates\prompts")) {
        Copy-Item (Join-Path $appDir "templates\prompts\*") (Join-Path $backup "templates_prompts\") -Force
    }
}

.\.venv\Scripts\pip install pyinstaller --quiet
.\.venv\Scripts\pyinstaller --noconfirm --clean --name GzhWorkbench --onedir run_app.py --add-data "templates;templates" --add-data "static;static"

if ($hasOld) {
    if (Test-Path (Join-Path $backup ".env")) {
        Copy-Item (Join-Path $backup ".env") (Join-Path $appDir ".env") -Force
    }
    foreach ($n in @("data", "storage")) {
        if (Test-Path (Join-Path $backup $n)) {
            Copy-Item (Join-Path $backup $n) $appDir -Recurse -Force
        }
    }
    if (Test-Path (Join-Path $backup "templates_prompts")) {
        New-Item -ItemType Directory -Force (Join-Path $appDir "templates\prompts") | Out-Null
        Copy-Item (Join-Path $backup "templates_prompts\*") (Join-Path $appDir "templates\prompts\") -Force
    }
    Remove-Item $backup -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "构建完成: backend\dist\GzhWorkbench\GzhWorkbench.exe"
Write-Host "已保留此前的 .env 配置、文章数据、图片与自定义提示词（如有）。"
Write-Host "使用: 把整个 GzhWorkbench 文件夹拷到任意位置，双击 GzhWorkbench.exe 即可。"
