# -*- coding: utf-8 -*-
"""历史研究 RAG 检索应用 — 入口。

启动方式：双击 启动Chroma管理界面.bat，或：
    D:\anaconda\envs\chroma\python.exe -m streamlit run app.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

import streamlit as st

st.set_page_config(page_title="历史研究 RAG 检索", page_icon="·", layout="wide")

import style  # noqa: E402

# 先注入全局样式，再渲染导航页，避免首次加载时出现一帧未美化的页面。
style.inject()

import core  # noqa: E402  提前触发 client 连接（加载 embedding 模型）

_conn_error = None
try:
    core.get_client()
    _conn_ok = True
except Exception as exc:
    _conn_ok = False
    _conn_error = str(exc)

pages = [
    st.Page("page_browse.py", title="浏览资料"),
    st.Page("page_manage.py", title="资料库管理"),
    st.Page("page_search.py", title="语义检索"),
    st.Page("page_import.py", title="批量导入"),
    st.Page("page_rag.py", title="检索增强问答"),
]

nav = st.navigation(pages, position="sidebar")
nav.run()

# ---- 侧边栏：状态 + 使用说明 ----
with st.sidebar:
    st.divider()
    if _conn_ok:
        st.success("✅ Chroma 已连接")
    else:
        st.error("❌ Chroma 连接失败")
        if _conn_error:
            with st.expander("查看错误详情"):
                st.code(_conn_error)
    st.caption(f"数据目录：`{core.CHROMA_PATH}`")

    if st.button("🔄 刷新库列表", use_container_width=True, key="global_refresh"):
        st.cache_data.clear()
        st.rerun()

    with st.expander("各页用途"):
        st.markdown(
            "- **浏览资料**：查看资料库、文献分布和文档内容\n"
            "- **资料库管理**：创建资料库、导入文档、管理 metadata\n"
            "- **语义检索**：按主题和语义查找相关材料，并导出结果\n"
            "- **批量导入**：批量导入 Markdown 等研究资料\n"
            "- **检索增强问答**：基于检索到的材料生成回答并核对来源"
        )

    with st.expander("⚡ 常见问题"):
        st.markdown(
            "- 先到「批量导入」建立资料库，再进行检索或问答\n"
            "- RAG 首次使用先在「LLM 设置」填 base_url / model，点「测试连接」\n"
            "- 导入过的文件重复导入会自动跳过，不会弄坏原数据"
        )
