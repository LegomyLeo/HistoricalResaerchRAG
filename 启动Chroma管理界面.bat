@echo off
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d D:\chroma_ui
echo 正在启动历史研究 RAG 检索...
start "" "D:\anaconda\envs\chroma\pythonw.exe" "D:\chroma_ui\desktop_app.py"
