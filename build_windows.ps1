$ErrorActionPreference = 'Stop'

# 在已配置好依赖的 Python 环境中生成 Windows 目录版应用。
# 用法：powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = if ($env:HISTORY_RAG_PYTHON) { $env:HISTORY_RAG_PYTHON } else { (Get-Command python).Source }

Push-Location $Root
try {
    & $Python -m pip install -r requirements.txt pyinstaller
    & $Python -m PyInstaller --noconfirm --clean --windowed `
        --name "HistoricalResearchRAG" `
        --add-data "config.json;." `
        desktop_app.py
    Write-Host "完成：$Root\dist\HistoricalResearchRAG"
} finally {
    Pop-Location
}
