# -*- coding: utf-8 -*-
"""页② 管理：库的新建/删除、手动添加、上传文件、删除文档、编辑 metadata。"""
import io
import json
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import streamlit as st

import core
import importer


def _validate_name(name: str) -> str:
    """校验库名称，返回错误信息；空串表示合法。"""
    if not name.strip():
        return "名称不能为空。"
    if len(name) < 3:
        return "名称至少 3 个字符。"
    if len(name) > 512:
        return "名称最多 512 个字符。"
    if name.startswith("_"):
        return "名称不能以 _ 开头。"
    return ""


def _count_label(name: str) -> str:
    try:
        n = core.collection_info(name)["count"]
        return f"{name}（{n} 条）"
    except Exception:
        return name


def render_manage() -> None:
    st.title("资料库管理")
    names = core.list_collections()

    tab_a, tab_b, tab_c, tab_d, tab_e = st.tabs([
        "新建/删除库", "手动添加", "上传文件", "删除文档", "编辑 metadata",
    ])

    # ============ Tab A 新建 / 删除库 ============
    with tab_a:
        st.subheader("新建向量库")
        st.caption("库名称 3–512 字符，不能以 _ 开头。距离空间建库后不可更改，新库建议用 cosine（相似度更直观）。")
        new_name = st.text_input("新库名称", key="manage_new_name")
        new_space = st.selectbox("距离空间", ["cosine", "l2"], index=0, key="manage_new_space",
                                 format_func=lambda s: "cosine（推荐）" if s == "cosine" else "l2（与旧库一致）")
        if st.button("创建", key="manage_create"):
            err = _validate_name(new_name)
            if err:
                st.error(err)
            elif new_name.strip() in names:
                st.warning("该库已存在。")
            else:
                try:
                    core.create_collection(new_name.strip(), space=new_space)
                    st.success(f"已创建向量库「{new_name.strip()}」（{new_space} 空间）")
                    st.rerun()
                except Exception as e:
                    st.error(f"创建失败：{e}")

        st.divider()
        st.subheader("删除向量库（不可恢复）")
        if names:
            del_name = st.selectbox("选择要删除的库", names, key="manage_del_sel",
                                    format_func=_count_label)
            confirm = st.checkbox(f"我确认删除「{del_name}」的全部数据，且不可恢复", key="manage_del_confirm")
            if st.button("删除", disabled=not confirm, key="manage_del_btn"):
                try:
                    core.delete_collection(del_name)
                    st.success(f"已删除「{del_name}」")
                    st.rerun()
                except Exception as e:
                    st.error(f"删除失败：{e}")
        else:
            st.caption("暂无向量库。")

    # ============ Tab B 手动添加 ============
    with tab_b:
        st.subheader("手动添加文档")
        if not names:
            st.info("请先到「新建/删除库」标签新建一个向量库。")
        else:
            target = st.selectbox("目标向量库", names, key="manage_add_target", format_func=_count_label)
            doc = st.text_area("文档内容", height=200, key="manage_add_doc")
            c1, c2, c3 = st.columns(3)
            doc_id = c1.text_input("id（留空自动生成）", key="manage_add_id")
            book = c2.text_input("书名", key="manage_add_book")
            chapter = c3.text_input("章节", key="manage_add_chapter")
            meta_json = st.text_area("metadata（JSON，可选，会与上方书名/章节合并）", value="{}", key="manage_add_meta")
            st.caption("提示：同一 id 再次添加会覆盖更新原文档。")
            if st.button("添加", key="manage_add_btn"):
                if not doc.strip():
                    st.warning("正文不能为空。")
                else:
                    try:
                        extra = json.loads(meta_json) if meta_json.strip() else {}
                    except json.JSONDecodeError as e:
                        st.error(f"metadata 不是合法 JSON：{e}")
                        return
                    final_id = doc_id.strip() or f"manual_{uuid.uuid4().hex}"
                    meta = {"book": book.strip(), "chapter": chapter.strip()}
                    meta.update(extra)
                    try:
                        core.get_collection(target).upsert(
                            ids=[final_id], documents=[doc], metadatas=[meta]
                        )
                        st.success(f"已添加，id = {final_id}")
                    except Exception as e:
                        st.error(f"添加失败：{e}")

    # ============ Tab C 上传文件 ============
    with tab_c:
        st.subheader("上传 .txt / .md 文件添加")
        if not names:
            st.info("请先新建一个向量库。")
        else:
            target = st.selectbox("目标向量库", names, key="manage_up_target", format_func=_count_label)
            st.caption(f"「{target}」当前已有 {core.collection_info(target)['count']} 条文档。")
            files = st.file_uploader(
                "选择文件（可多选）", type=["txt", "md"], accept_multiple_files=True,
                key="manage_up_files",
            )
            split_on = st.checkbox("按 ## 标题切片后入库（推荐）", value=True, key="manage_up_split")
            if files and st.button("预览切片", key="manage_up_preview"):
                preview_rows = []
                for f in files:
                    try:
                        text = f.getvalue().decode("utf-8-sig")
                    except UnicodeDecodeError:
                        st.error(f"{f.name} 不是 UTF-8 编码，已跳过。")
                        continue
                    if split_on:
                        _, chs = importer.slice_md_by_heading(text)
                        preview_rows.append({
                            "文件": f.name,
                            "预计块数": len(chs),
                            "总字符": len(text),
                        })
                    else:
                        preview_rows.append({"文件": f.name, "预计块数": 1, "总字符": len(text)})
                if preview_rows:
                    st.dataframe(pd.DataFrame(preview_rows), width="stretch", hide_index=True)
                    st.caption(f"预计共 {sum(r['预计块数'] for r in preview_rows)} 条。导入会计算向量，耗时取决于数据量。")
            if files and st.button("确认导入", key="manage_up_go"):
                col = core.get_collection(target)
                total_added = 0
                prog = st.progress(0.0)
                for fi, f in enumerate(files):
                    try:
                        text = f.getvalue().decode("utf-8-sig")
                    except UnicodeDecodeError:
                        st.error(f"{f.name} 非 UTF-8，已跳过。")
                        continue
                    if split_on:
                        book, chs = importer.slice_md_by_heading(text)
                        records = []
                        for idx, (title, body, sub) in enumerate(chs):
                            records.append((
                                importer.make_id(f.name, title, sub),
                                body,
                                importer.build_metadata(f.name, f.name, book, title, sub, body),
                            ))
                    else:
                        records = [(
                            importer.make_id(f.name, "全文", 0),
                            text,
                            importer.build_metadata(f.name, f.name, f.name, "全文", 0, text),
                        )]
                    batch = 200
                    for start in range(0, len(records), batch):
                        chunk = records[start:start + batch]
                        col.upsert(
                            ids=[r[0] for r in chunk],
                            documents=[r[1] for r in chunk],
                            metadatas=[r[2] for r in chunk],
                        )
                    total_added += len(records)
                    prog.progress((fi + 1) / len(files))
                st.success(f"已导入 {total_added} 条（同一文件重复导入会自动覆盖更新）。")

    # ============ Tab D 删除文档 ============
    with tab_d:
        if not names:
            st.info("还没有向量库。")
        else:
            # ---- 按 id 删除（目标库始终可见，流程清晰） ----
            st.subheader("按 id 删除")
            id_col = st.selectbox("目标库", names, key="manage_del_ids_col", format_func=_count_label)
            ids_input = st.text_input("id（多个用英文逗号分隔）", key="manage_del_ids",
                                      placeholder="如：a1b2c3..., d4e5f6...（可到浏览页查看 id）")
            if ids_input.strip() and st.button("删除这些 id", key="manage_del_ids_btn"):
                id_list = [i.strip() for i in ids_input.split(",") if i.strip()]
                if id_list:
                    col = core.get_collection(id_col)
                    try:
                        col.delete(ids=id_list)
                        st.success(f"已删除 {len(id_list)} 条（未存在的 id 会自动忽略）。")
                    except Exception as e:
                        st.error(f"删除失败：{e}")

            st.divider()

            # ---- 按条件删除（预览命中后二次确认） ----
            st.subheader("按条件删除")
            wcol = st.selectbox("目标库", names, key="manage_where_col", format_func=_count_label)
            where_expr = st.text_input(
                "条件，格式：字段=值（如 filename=宋史.md，book=宋史）", key="manage_where_expr"
            )
            if where_expr.strip() and "=" in where_expr:
                k, v = where_expr.split("=", 1)
                k, v = k.strip(), v.strip()
                col = core.get_collection(wcol)
                try:
                    hit = col.get(where={k: v}, limit=200, include=["documents"])
                    hit_ids = list(hit.get("ids") or [])
                except Exception as e:
                    hit_ids = None
                    st.error(f"条件无效：{e}")
                if hit_ids is not None:
                    if not hit_ids:
                        st.info(f"没有匹配「{k}={v}」的文档。")
                    else:
                        st.caption(f"将删除 {len(hit_ids)} 条（最多预览前 200 条 id）：")
                        st.code("\n".join(hit_ids[:20]) + ("\n…" if len(hit_ids) > 20 else ""), language=None)
                        confirm = st.checkbox(
                            f"我确认删除匹配「{k}={v}」的全部 {len(hit_ids)} 条（不可恢复）",
                            key="manage_where_confirm",
                        )
                        if confirm and st.button("执行删除", key="manage_where_btn"):
                            col.delete(where={k: v})
                            st.success(f"已删除匹配「{k}={v}」的 {len(hit_ids)} 条。")

            st.divider()

            # ---- 清空库 ----
            st.subheader("清空向量库")
            clear_col = st.selectbox("选择要清空的库", names, key="manage_clear_col", format_func=_count_label)
            clear_confirm = st.checkbox(
                f"我确认清空「{clear_col}」的全部文档（保留库本身，不可恢复）", key="manage_clear_confirm"
            )
            if clear_confirm and st.button("清空", key="manage_clear_btn"):
                n = core.clear_collection(clear_col)
                st.success(f"已清空 {n} 条文档。")

    # ============ Tab E 编辑 metadata ============
    with tab_e:
        st.subheader("编辑 metadata")
        st.caption("metadata 是与文档绑定的附加信息（书名、章节、来源文件等）。这里按表格键值编辑，id 与正文不可改。")
        if not names:
            st.info("还没有向量库。")
        else:
            ecol = st.selectbox("目标库", names, key="manage_edit_col", format_func=_count_label)
            col = core.get_collection(ecol)
            try:
                sample = col.get(limit=200, include=["documents", "metadatas"])
            except Exception:
                sample = {}
            sample_ids = list(sample.get("ids") or [])
            if not sample_ids:
                st.caption("该库暂无文档。")
            else:
                # 建立 id → (doc, meta) 映射，方便选择
                doc_map = {}
                for i, sid in enumerate(sample_ids):
                    metas = sample.get("metadatas") or []
                    docs = sample.get("documents") or []
                    doc_map[sid] = (
                        (docs[i] if i < len(docs) else ""),
                        dict((metas[i]) or {}) if i < len(metas) else {},
                    )
                pick = st.selectbox(
                    "选择要编辑的文档", sample_ids,
                    key="manage_edit_pick",
                    format_func=lambda sid: _pick_label(doc_map, sid),
                )
                doc_text, meta = doc_map.get(pick, ("", {}))

                with st.expander("查看该文档正文（只读）", expanded=False):
                    st.code(doc_text or "(空)", language=None)

                # 键值表编辑
                default_rows = [{"字段": k, "值": v if not isinstance(v, (list, dict)) else json.dumps(v, ensure_ascii=False)}
                                for k, v in meta.items()]
                if not default_rows:
                    default_rows = [{"字段": "", "值": ""}]
                edited = st.data_editor(
                    pd.DataFrame(default_rows),
                    num_rows="dynamic",
                    key="manage_edit_grid",
                    column_config={
                        "字段": st.column_config.TextColumn("字段", width="medium", help="如 book / chapter / filename"),
                        "值": st.column_config.TextColumn("值", width="large"),
                    },
                    hide_index=True,
                    width="stretch",
                )
                st.caption("可新增行、删除行；字段为空的整行会被忽略。复杂值（列表/字典）请填 JSON 文本。")
                if st.button("保存 metadata", key="manage_edit_save"):
                    new_meta = {}
                    bad = False
                    for _, row in edited.iterrows():
                        k = str(row["字段"]).strip() if row["字段"] is not None else ""
                        v = row["值"]
                        if not k:
                            continue
                        if isinstance(v, str) and v.strip().startswith(("{", "[")):
                            try:
                                v = json.loads(v)
                            except json.JSONDecodeError:
                                bad = True
                                st.error(f"字段「{k}」的值不是合法 JSON：{v[:50]}…")
                                break
                        new_meta[k] = v
                    if not bad:
                        try:
                            col.update(ids=[pick], metadatas=[new_meta])
                            st.success(f"已更新 {pick} 的 metadata（{len(new_meta)} 个字段）。")
                        except Exception as e:
                            st.error(f"保存失败：{e}")


def _pick_label(doc_map: dict, sid: str) -> str:
    doc, meta = doc_map.get(sid, ("", {}))
    book = meta.get("book", "") or ""
    chapter = meta.get("chapter", "") or ""
    head = book or chapter or "(无书名)"
    return f"{head} · {sid[:16]}"


if __name__ == "__main__":
    # st.navigation 会把本文件当作 __main__ 执行；必须在此调用渲染函数
    render_manage()
