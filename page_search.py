# -*- coding: utf-8 -*-
"""页③ 语义搜索：当前库/全库搜索 + 按书过滤 + 相似度阈值 + 结果导出。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import streamlit as st

import core

# 书名列表（分钟级缓存，导入新书后一分钟后自动刷新）
@st.cache_data(ttl=60, show_spinner=False)
def _book_list(collection: str) -> list:
    try:
        bk = core.collection_breakdown(collection)["books"]
        return sorted(bk.keys())
    except Exception:
        return []


def _query_one(col, q, n, where):
    res = col.query(
        query_texts=[q], n_results=n, where=where,
        include=["documents", "metadatas", "distances"],
    )
    docs = res.get("documents") and res["documents"][0] or []
    dists = res.get("distances") and res["distances"][0] or []
    metas = res.get("metadatas") and res["metadatas"][0] or []
    out = []
    for i in range(len(docs)):
        m = metas[i] if i < len(metas) else {}
        d = float(dists[i]) if i < len(dists) else 0.0
        out.append({"sim": 1 / (1 + d), "dist": d, "doc": docs[i], "meta": m or {}})
    return out


def render_search() -> None:
    st.title("语义检索")
    names = core.list_collections()
    if not names:
        st.info("还没有向量库。请先到「📥 批量导入」页导入数据。")
        return

    # ---- 输入区 ----
    with st.container(border=True):
        st.caption("输入想找的内容，按意思检索（不要求关键词完全一致）。")
        scope = st.radio("搜索范围", ["全部向量库", "指定向量库"], index=0, horizontal=True, key="search_scope")
        sel = st.selectbox("选择向量库", names, key="search_sel") if scope == "指定向量库" else None

        cq, cn = st.columns([3, 1])
        q = cq.text_input("查询内容", placeholder="如：金代诗歌、王安石变法", key="search_q")
        n = cn.slider("每库返回条数", 1, 20, 5, key="search_n")

        c1, c2 = st.columns(2)
        if sel:
            books = _book_list(sel)
            book_filter = c1.selectbox("按书名过滤（可选）", ["（不过滤）"] + books, key="search_bookf") if books else "（不过滤）"
            if book_filter == "（不过滤）":
                book_filter = "（不过滤）"
        else:
            book_filter = "（不过滤）"
            c1.caption("全库模式下可按 metadata 字段过滤（见右）")
        where = None
        wf = c2.text_input("字段过滤（可选，如 book）", key="search_wf", placeholder="留空不启用")
        wv = c2.text_input("过滤值（可选，如 宋史）", key="search_wv", placeholder="对应值")
        if book_filter != "（不过滤）":
            where = {"book": book_filter}
        elif wf.strip() and wv.strip():
            where = {wf.strip(): wv.strip()}

        min_sim = st.slider("最低相似度（低于此分不显示）", 0.0, 1.0, 0.0, 0.05, key="search_minsim")
        st.caption("提示：距离度量在建库时已固定；cosine 空间仅对新建库生效。检索用本地 all-MiniLM-L6-v2 模型，不联网。")
        search_clicked = st.button("搜索", key="search_btn", type="primary", disabled=not q.strip())

    # ---- 结果区 ----
    if not search_clicked or not q.strip():
        return
    results = []
    target_cols = names if sel is None else [sel]
    for nm in target_cols:
        try:
            r = _query_one(core.get_collection(nm), q.strip(), n, where)
            for item in r:
                item["向量库"] = nm
            results.extend(r)
        except Exception as e:
            st.warning(f"「{nm}」查询失败：{e}")
    if not results:
        st.warning("没有命中结果。")
        return
    results.sort(key=lambda x: x["sim"], reverse=True)
    results = [r for r in results if r["sim"] >= min_sim]
    if not results:
        st.warning(f"低于最低相似度 {min_sim}，无结果。可调低阈值再试。")
        return

    st.success(f"找到 {len(results)} 条结果")

    rows = []
    for r in results:
        m = r["meta"]
        rows.append({
            "相似度": round(r["sim"], 4),
            "距离": round(r["dist"], 4),
            "向量库": r["向量库"],
            "书名": m.get("book", "") if m else "",
            "章节": m.get("chapter", "") if m else "",
            "来源文件": m.get("filename", "") if m else "",
            "片段": (r["doc"] or "")[:100] + ("…" if len(r["doc"] or "") > 100 else ""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)

    dc1, dc2 = st.columns(2)
    csv = df.to_csv(index=False).encode("utf-8-sig")
    dc1.download_button("⬇️ 下载 CSV（可用 Excel 打开）", data=csv,
                        file_name=f"检索结果_{q.strip()[:12]}.csv", mime="text/csv", key="search_csv")
    if dc2.button("📋 复制结果为 Markdown 表格", key="search_copy"):
        st.code(df.to_markdown(index=False), language="markdown")
        st.success("已生成，请手动复制上方表格。")

    st.subheader("命中详情")
    for r in results:
        m = r["meta"]
        book = m.get("book", "") if m else ""
        chapter = m.get("chapter", "") if m else ""
        coll = r["向量库"]
        with st.expander(f"[{r['sim']:.3f}] {coll} · {book} · {chapter}"):
            st.code(r["doc"] or "(空)", language=None)
            if m:
                st.json(m)


if __name__ == "__main__":
    # st.navigation 会把本文件当作 __main__ 执行；必须在此调用渲染函数
    render_search()
