# Historical Research RAG

面向历史研究者的本地资料检索与检索增强问答应用。

## 本地运行

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

应用数据默认保存到当前用户的 `LocalAppData\\HistoricalResearchRAG` 目录。API key 通过环境变量配置，不写入仓库。

## 构建 macOS 安装包

仓库中的 GitHub Actions 会在推送 `v*` 标签或手动运行时，使用 macOS 云端构建环境生成 Intel 和 Apple Silicon 两个 `.dmg` 文件。构建完成后，在 GitHub Actions 对应任务的 Artifacts 中下载。

未签名版本首次打开时，macOS 可能需要在“系统设置 → 隐私与安全性”中手动允许打开。正式公开发布时，建议使用 Apple Developer 账号完成签名和公证。
