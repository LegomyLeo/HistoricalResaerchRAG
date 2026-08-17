# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for package in ("streamlit", "chromadb", "webview"):
    try:
        d, b, h = collect_all(package)
        datas += d
        binaries += b
        hiddenimports += [name for name in h if ".tests" not in name and not name.endswith(".test")]
    except Exception:
        pass

for filename in (
    "app.py", "core.py", "style.py", "llm.py", "importer.py", "login.py",
    "page_browse.py", "page_manage.py", "page_search.py", "page_import.py", "page_rag.py",
    "config.json",
):
    datas.append((filename, "."))

a = Analysis(
    ["desktop_app.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="HistoricalResearchRAG",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
