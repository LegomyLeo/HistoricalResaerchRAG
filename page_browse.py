# -*- coding: utf-8 -*-
"""页① 浏览：collection 总览 + 指标 + 书目分布 + 按书过滤分页浏览。"""
import math
import sys

sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import streamlit as st

import core

PAGE_SIZE = 20


def _fmt_chars(n: int) -> str:
    if n >= 10_000:
        return f"{n / 10_000:.1f} 万"
    if n >= 1000:
        return f"{n / 1000:.1f} 千"
    return str(n)


def render_browse() -> None:
    st.title("浏览资料库")
    names = core.list_collections()

    if not names:
        st.info("还没有任何向量库。请到「🗂️ 库与文档管理」页新建，或「📥 批量导入」页导入数据。")
        return

    # ---- 总览卡 ----
    c1, c2 = st.columns(2)
    total_docs = sum(core.collection_info(n)["count"] for n in names)
    c1.metric("向量库总数", len(names))
    c2.metric("文档总数", total_docs)

    st.divider()

    # ---- 选库 ----
    sel = st.selectbox("选择向量库", names, key="browse_sel")
    if not sel:
        return

    col = core.get_collection(sel)
    info = core.collection_info(sel)
    breakdown = core.collection_breakdown(sel)
    src_files = len(breakdown["files"])

    # ---- 指标 ----
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("文档数", info["count"])
    mc2.metric("向量维度", info["dimension"] if info["dimension"] else "—")
    mc3.metric("距离空间", info["space"])
    mc4.metric("来源文件数", src_files)
    mc5.metric("总字符", _fmt_chars(breakdown["total_chars"]) if breakdown["total_chars"] else "—")

    # ---- 书目分布 ----
    if breakdown["books"]:
        with st.expander(f"📚 书目分布（{len(breakdown['books'])} 种书）", expanded=False):
            bdf = pd.DataFrame(
                [{"书名": b, "条数": n} for b, n in sorted(breakdown["books"].items(), key=lambda kv: -kv[1])]
            )
            st.dataframe(bdf, width="stretch", hide_index=True)
            st.caption("按「书名」metadata 统计。若统计不准，可能是导入时 metadata 里书名不一致。")

    if info["count"] == 0:
        st.info("该向量库为空。可到「📥 批量导入」页导入数据。")
        return

    # ---- 按书名过滤 ----
    book_list = sorted(breakdown["books"].keys())
    filter_book = st.selectbox("只看某本书（默认全部）", ["（全部）"] + book_list, key="browse_filter_book")

    # 切换库或书目后，旧页码可能超出新结果范围；自动回到第一页。
    browse_scope = (sel, filter_book)
    if st.session_state.get("browse_scope") != browse_scope:
        st.session_state.browse_scope = browse_scope
        st.session_state.browse_page = 1

    # 过滤后计数（仅当选中具体书时）
    shown_count = info["count"]
    if filter_book != "（全部）":
        try:
            shown_count = breakdown["books"].get(filter_book, 0)
        except Exception:
            pass
    if shown_count == 0:
        st.info("当前过滤条件下没有文档。")
        return

    # ---- 分页 ----
    total_pages = max(1, math.ceil(shown_count / PAGE_SIZE))
    current_page = min(max(1, int(st.session_state.get("browse_page", 1))), total_pages)
    st.session_state.browse_page = current_page
    pc1, pc2, pc3 = st.columns([1, 3, 1])
    with pc1:
        if st.button("◀ 上一页", key="browse_prev", disabled=st.session_state.get("browse_page", 1) <= 1):
            st.session_state.browse_page = max(1, st.session_state.get("browse_page", 1) - 1)
    with pc2:
        page = st.number_input("页码", 1, total_pages, current_page, key="browse_page")
    with pc3:
        if st.button("下一页 ▶", key="browse_next", disabled=page >= total_pages):
            st.session_state.browse_page = min(total_pages, page + 1)
    st.caption(f"当前显示 {shown_count} 条 · 每页 {PAGE_SIZE} 条 · 第 {page}/{total_pages} 页")

    # ---- 拉数据 ----
    offset = (page - 1) * PAGE_SIZE
    where = {"book": filter_book} if filter_book != "（全部）" else None
    try:
        res = col.get(
            limit=PAGE_SIZE,
            offset=offset,
            where=where,
            include=["documents", "metadatas"],
        )
    except Exception as e:
        st.error(f"读取失败：{e}")
        return

    ids = res.get("ids") or []
    docs = res.get("documents") or []
    metas = res.get("metadatas") or []

    rows = []
    for i, doc_id in enumerate(ids):
        doc = docs[i] if i < len(docs) else ""
        meta = metas[i] if i < len(metas) else {}
        rows.append({
            "id": doc_id,
            "书名": meta.get("book", "") if meta else "",
            "章节": meta.get("chapter", "") if meta else "",
            "来源文件": meta.get("filename", "") if meta else "",
            "字符数": len(doc or ""),
            "内容预览": (doc or "")[:80] + ("…" if len(doc or "") > 80 else ""),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    # ---- 查看全文 ----
    st.subheader("查看全文 / metadata")
    for i, doc_id in enumerate(ids):
        doc = docs[i] if i < len(docs) else ""
        meta = metas[i] if i < len(metas) else {}
        book = meta.get("book", "") if meta else ""
        chapter = meta.get("chapter", "") if meta else ""
        title = f"{book} · {chapter} · {doc_id}" if book else doc_id
        with st.expander(title):
            st.code(doc or "(空)", language=None)
            if meta:
                st.write("**metadata**")
                st.json(meta)


if __name__ == "__main__":
    # st.navigation 会把本文件当作 __main__ 执行；必须在此调用渲染函数
    render_browse()
