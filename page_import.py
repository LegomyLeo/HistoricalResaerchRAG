# -*- coding: utf-8 -*-
"""页④ 史库批量导入：可选文件夹 + 过滤说明 + 切片 + 幂等导入 + 结果横幅。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import streamlit as st

import core
import importer

DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Documents")
BATCH = 200


def render_import_page() -> None:
    st.title("批量导入资料")
    st.caption(
        "流程：① 填文件夹路径 → ② 列出文件并勾选 → ③ 选目标库和切片方式 → ④ 预览 → ⑤ 开始导入。"
        "已导入过的文件再次导入会自动「跳过」，不会重复。"
    )

    # ---- 上次导入结果横幅（修复：st.rerun 会冲掉即时提示，改从 session_state 常驻显示） ----
    if st.session_state.get("import_result"):
        r = st.session_state.import_result
        if r.get("errors"):
            st.error(f"上次导入：新增 {r['added']} 条 / 跳过（已存在）{r['skipped']} 条 / 失败 {len(r['errors'])} 条")
            for e in r["errors"]:
                st.write(f"- {e}")
        else:
            st.success(f"上次导入完成：新增 {r['added']} 条，跳过（已存在）{r['skipped']} 条。")
        if st.button("清除提示", key="import_clear_res"):
            del st.session_state.import_result
            st.rerun()
        st.divider()

    # ---- 1. 源目录 ----
    with st.container(border=True):
        folder = st.text_input(
            "文件夹路径",
            value=st.session_state.get("import_folder", DEFAULT_DIR),
            key="import_folder",
        )
        st.caption("可改为任意文件夹；自动跳过 *.bak_* 备份、*校对报告.md（可在下方勾选包含）、*_assets 目录。")
        include_report = st.checkbox("包含校对报告（默认否）", value=False, key="import_include_report")
        scan_btn = st.button("📂 列出该文件夹的 .md 文件", key="import_scan")
    if scan_btn or st.session_state.get("import_candidates") is not None:
        inc, exc = importer.scan_folder(
            folder.strip() if folder.strip() else DEFAULT_DIR, include_report=include_report
        )
        st.session_state.import_candidates = inc
        st.session_state.import_excluded = exc
        if not inc:
            st.warning("该文件夹下没有可导入的 .md 文件（或路径不存在）。")
            if exc:
                with st.expander(f"已自动跳过 {len(exc)} 项（下方列表）", expanded=True):
                    for name, reason in exc[:50]:
                        st.write(f"- {os.path.basename(name)} — {reason}")
            return

        st.success(f"发现 {len(inc)} 个可导入文件。")
        if exc:
            with st.expander(f"已自动跳过 {len(exc)} 项（备份/校对报告/_assets 等）", expanded=False):
                for name, reason in exc[:100]:
                    st.write(f"- {os.path.basename(name)} — {reason}")
                if len(exc) > 100:
                    st.caption(f"… 还有 {len(exc) - 100} 项")

        # ---- 2. 文件多选 ----
        st.subheader("选择要导入的文件")
        csel, csel2 = st.columns([3, 1])
        with csel:
            fmt = lambda c: f"{c['name']}（{c['size_kb']}KB）"
            sel_files = st.multiselect("文件", inc, format_func=fmt, key="import_sel_files")
        with csel2:
            if st.button("全选正本", key="import_sel_all"):
                st.session_state.import_sel_files = [c for c in inc if not c["name"].endswith("校对报告.md")]
                st.rerun()
            if st.button("全不选", key="import_sel_none"):
                st.session_state.import_sel_files = []
                st.rerun()

        if not sel_files:
            return

        # ---- 3. 目标 collection ----
        st.subheader("导入到")
        names = core.list_collections()
        new_name = st.text_input("或新建库（填名字；为空则用下方选择）", key="import_new_name")
        if names:
            target = st.selectbox(
                "目标向量库", names, key="import_target",
                format_func=lambda nm: f"{nm}（已有 {core.collection_info(nm)['count']} 条）",
            )
        else:
            target = None
        if new_name.strip():
            eff_target = new_name.strip()
        else:
            eff_target = target
        if not eff_target:
            st.info("请选择或新建一个目标向量库。")
            return
        if eff_target in names:
            _existing = core.collection_info(eff_target)["count"]
            st.caption(f"将导入到「{eff_target}」（已有 {_existing} 条文档）；同名切片 id 已存在时会跳过（幂等）。")
        else:
            st.caption(f"将新建库「{eff_target}」并导入；同名切片 id 已存在时会跳过（幂等）。")

        # ---- 4. 切片策略 ----
        st.subheader("切片策略")
        mode = st.radio(
            "切片方式",
            ["按 ## 二级标题切块（推荐）", "整文件一条", "按 ## 且超长章节再拆分"],
            key="import_mode",
        )
        max_chars = 2000
        if mode.startswith("按 ## 且超长"):
            max_chars = st.slider("单块最大字符数", 500, 5000, 2000, key="import_maxchars")
        mode_key = {"按 ## 二级标题切块（推荐）": "heading", "整文件一条": "whole", "按 ## 且超长章节再拆分": "split"}[mode]

        # ---- 5. 预览 ----
        if st.button("🔍 预览切块", key="import_preview"):
            rows = []
            for f in sel_files:
                try:
                    text = importer.read_text(f["path"])
                except Exception as e:
                    st.error(f"{f['name']} 读取失败：{e}")
                    continue
                _, recs = importer.slice_for_import(text, mode_key, max_chars)
                rows.append({"文件": f["name"], "预计块数": len(recs), "总字符": len(text)})
            if rows:
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
                total = sum(r["预计块数"] for r in rows)
                st.caption(f"预计共 {total} 条。导入会计算向量，耗时取决于数据量（约每分钟数百条）。")

        # ---- 6. 开始导入 ----
        if st.button("🚀 开始导入", type="primary", key="import_go"):
            col = core.get_collection(eff_target)
            prog = st.progress(0.0)
            status = st.status("正在导入…", expanded=True)
            summary = {"added": 0, "skipped": 0, "updated": 0, "errors": []}
            total_files = len(sel_files)

            for fi, f in enumerate(sel_files):
                try:
                    text = importer.read_text(f["path"])
                except Exception as e:
                    summary["errors"].append(f"{f['name']}: {e}")
                    prog.progress((fi + 1) / total_files)
                    continue
                _, recs = importer.slice_for_import(text, mode_key, max_chars)
                ids = [importer.make_id(f["name"], title, sub) for (title, _, sub) in recs]
                docs = [body for (_, body, _) in recs]
                metas = [
                    importer.build_metadata(f["name"], f["path"], book, title, sub, body)
                    for (title, body, sub) in recs
                ]

                # 幂等：查已有 id
                existing_ids = set()
                for start in range(0, len(ids), 500):
                    try:
                        ex = col.get(ids=ids[start:start + 500], include=[])
                        existing_ids.update(ex.get("ids") or [])
                    except Exception:
                        pass

                new_ids, new_docs, new_metas = [], [], []
                for i, did in enumerate(ids):
                    if did in existing_ids:
                        summary["skipped"] += 1
                    else:
                        new_ids.append(did)
                        new_docs.append(docs[i])
                        new_metas.append(metas[i])

                for start in range(0, len(new_ids), BATCH):
                    chunk_ids = new_ids[start:start + BATCH]
                    col.upsert(
                        ids=chunk_ids,
                        documents=new_docs[start:start + BATCH],
                        metadatas=new_metas[start:start + BATCH],
                    )
                summary["added"] += len(new_ids)
                status.write(f"✓ {f['name']}：新增 {len(new_ids)}，跳过 {len(ids) - len(new_ids)}")
                prog.progress((fi + 1) / total_files)

            status.update(
                label=f"完成：新增 {summary['added']} / 跳过 {summary['skipped']} / 失败 {len(summary['errors'])}",
                state="complete",
            )
            st.session_state.import_result = summary


if __name__ == "__main__":
    # st.navigation 会把本文件当作 __main__ 执行；必须在此调用渲染函数
    render_import_page()
