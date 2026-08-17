# Historical Research RAG

面向历史研究者的本地资料检索与检索增强问答应用。

## 本地运行

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

应用数据默认保存到当前用户的 `LocalAppData\\HistoricalResearchRAG` 目录。API key 通过环境变量配置，不写入仓库。
