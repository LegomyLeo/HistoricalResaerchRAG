# -*- coding: utf-8 -*-
"""页⑤ RAG 问答：Chroma 检索 + LLM 后端生成（自建 vLLM / API key 可切换，支持测试连接）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import streamlit as st

import core
import llm

DEFAULT_SYSTEM = (
    "你是历史研究助手。请严格依据提供的史料上下文回答用户问题；"
    "若上下文不足以回答，请如实说明，不要编造。回答中可注明所引用的史料来源。"
)


def _backend_badge(cfg: dict) -> str:
    mode = cfg.get("backend_mode", "vllm")
    b = cfg.get(mode, {})
    model = (b.get("model") or "未设置")
    if mode == "vllm":
        return f"自建 vLLM · {model}"
    return f"API key · {model}"


def render_rag() -> None:
    st.title("检索增强问答")
    st.caption("从向量库检索相关史料片段，交给 LLM 生成回答。答案下方会列出引用的史料来源，可核对。")

    names = core.list_collections()
    if not names:
        st.info("还没有向量库，请先导入数据。")
        return

    # ---- LLM 配置 ----
    cfg = llm.load_config()
    with st.expander("⚙️ LLM 设置", expanded=False):
        mode = st.radio(
            "后端模式",
            ["vllm", "apikey"],
            index=0 if cfg.get("backend_mode") == "vllm" else 1,
            format_func=lambda m: "自建 vLLM / 开源模型（OpenAI 兼容）" if m == "vllm" else "云 API 服务（OpenAI / DeepSeek 等）",
            key="rag_mode",
        )
        cfg["backend_mode"] = mode
        b = cfg[mode]
        base_url = st.text_input(
            "base_url（OpenAI 兼容地址）",
            value=b.get("base_url", ""),
            key="rag_base_url",
            help="自建/云 GPU vLLM 示例：http://<IP>:8000/v1（本地或任意云主机）；云 API 示例：https://api.openai.com/v1 或 https://api.deepseek.com/v1",
        )
        env_name = "CHROMA_LLM_API_KEY" if mode == "apikey" else "CHROMA_VLLM_API_KEY"
        st.info(f"API key 不保存在配置文件中，请通过环境变量 `{env_name}` 设置。", icon="🔐")
        model = st.text_input("model", value=b.get("model", ""), key="rag_model", help="填你服务里部署/订阅的模型名，如 Qwen3-8B / gpt-4o-mini / deepseek-chat")
        temperature = st.slider("temperature", 0.0, 1.5, float(b.get("temperature", 0.7)), 0.1, key="rag_temp")
        b.update({"base_url": base_url, "model": model, "temperature": temperature})
        system_prompt = st.text_area("System 提示词", value=cfg.get("system_prompt", DEFAULT_SYSTEM), key="rag_system")
        cfg["system_prompt"] = system_prompt

        tc1, tc2 = st.columns([1, 2])
        with tc1:
            if st.button("🔌 测试连接", key="rag_test"):
                if not base_url.strip() or not model.strip():
                    st.error("请先填写 base_url 和 model。")
                else:
                    with st.spinner("正在连接后端…"):
                        try:
                            reply = llm.chat(cfg, [{"role": "user", "content": "你好，请回复：连接成功"}])
                            st.success(f"连接成功！后端回复：{reply[:80]}")
                        except RuntimeError as e:
                            st.error(f"连接失败：{e}")
                        except Exception as e:
                            st.error(f"连接失败（未知错误）：{e}")
        with tc2:
            if st.button("💾 保存 LLM 配置", key="rag_save"):
                llm.save_config(cfg)
                st.success("配置已保存到 config.json。")
        st.caption("密钥仅从环境变量读取；修改后请重启应用或重新打开本页。")

    # ---- 检索 ----
    sel = st.selectbox("选择向量库", names, key="rag_sel")

    with st.container(border=True):
        st.caption(f"当前后端：**{_backend_badge(cfg)}**（可在上方「⚙️ LLM 设置」修改）")
        c1, c2 = st.columns([3, 1])
        with c1:
            question = st.text_area("提问", placeholder="如：王安石变法在宋史中有哪些记载？", key="rag_q")
        with c2:
            top_k = st.slider("检索条数", 1, 10, 4, key="rag_topk")
            if st.button("🧹 清空提问", key="rag_clear"):
                st.session_state.rag_q = ""
                st.rerun()
        go = st.button("🔍 检索并回答", type="primary", key="rag_go", disabled=not question.strip())

    # ---- 结果区（容器外，主区更干净） ----
    if not go:
        return

    backend = llm.active_backend(cfg)
    if not (backend.get("base_url") or "").strip() or not (backend.get("model") or "").strip():
        st.error("请先在「⚙️ LLM 设置」里填写 base_url 和 model，再点「🔌 测试连接」确认可通。")
        return

    col = core.get_collection(sel)
    try:
        res = col.query(
            query_texts=[question.strip()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        st.error(f"检索失败：{e}")
        return

    docs = res.get("documents") and res["documents"][0] or []
    dists = res.get("distances") and res["distances"][0] or []
    metas = res.get("metadatas") and res["metadatas"][0] or []

    if not docs:
        st.warning("没有检索到相关内容。可换关键词或降低 top_k。")
        return

    st.subheader(f"检索到的 {len(docs)} 条片段")
    rows = []
    for i, doc in enumerate(docs):
        dist = float(dists[i]) if i < len(dists) else 0.0
        meta = metas[i] if i < len(metas) else {}
        rows.append({
            "相似度": round(1 / (1 + dist), 4),
            "书名": meta.get("book", "") if meta else "",
            "章节": meta.get("chapter", "") if meta else "",
            "来源文件": meta.get("filename", "") if meta else "",
            "片段": (doc or "")[:120] + ("…" if len(doc or "") > 120 else ""),
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    context_parts = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        book = meta.get("book", "") if meta else ""
        chapter = meta.get("chapter", "") if meta else ""
        context_parts.append(f"【史料{i + 1}｜{book}·{chapter}】\n{doc}")
    context = "\n\n".join(context_parts)

    with st.spinner("正在调用 LLM 生成回答…"):
        messages = llm.build_rag_messages(system_prompt or DEFAULT_SYSTEM, context, question.strip())
        try:
            answer = llm.chat(cfg, messages)
        except RuntimeError as e:
            st.error(f"LLM 调用失败：{e}")
            st.info("请检查「⚙️ LLM 设置」里的 base_url / api_key / model 是否正确，或先用「🔌 测试连接」验证。")
            return

    st.subheader("回答")
    st.markdown(answer)
    st.download_button(
        "⬇️ 下载回答为 .md",
        data=(f"# 问题\n{question.strip()}\n\n# 回答\n{answer}\n\n# 引用来源\n" + "\n".join(
            f"- [{m.get('book','')}·{m.get('chapter','')}]({m.get('filename','')})" for m in metas if m
        )).encode("utf-8"),
        file_name="RAG回答.md",
        mime="text/markdown",
        key="rag_dl",
    )

    st.subheader("引用来源")
    for i, doc in enumerate(docs):
        dist = float(dists[i]) if i < len(dists) else 0.0
        meta = metas[i] if i < len(metas) else {}
        book = meta.get("book", "") if meta else ""
        chapter = meta.get("chapter", "") if meta else ""
        with st.expander(f"[{1/(1+dist):.3f}] {book} · {chapter}"):
            st.code(doc or "(空)", language=None)
            if meta:
                st.json(meta)


if __name__ == "__main__":
    # st.navigation 会把本文件当作 __main__ 执行；必须在此调用渲染函数
    render_rag()
