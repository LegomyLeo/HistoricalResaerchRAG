# -*- coding: utf-8 -*-
"""共享层：PersistentClient 单例 + collection 工具函数。"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

import chromadb
import streamlit as st

APP_DATA_DIR = os.environ.get(
    "HISTORY_RAG_DATA_DIR",
    os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "HistoricalResearchRAG", "data"),
)
CHROMA_PATH = os.path.abspath(APP_DATA_DIR)
os.makedirs(CHROMA_PATH, exist_ok=True)


@st.cache_resource(show_spinner="连接 Chroma 并加载向量模型...")
def get_client() -> chromadb.PersistentClient:
    """进程级单例 client（跨页面 / 跨 rerun 复用，避免重复加载 embedding 模型）。"""
    return chromadb.PersistentClient(path=CHROMA_PATH)


def list_collections() -> list:
    """返回按名称排序的 collection 列表。"""
    client = get_client()
    names = []
    for c in client.list_collections():
        name = getattr(c, "name", None) or (c if isinstance(c, str) else str(c))
        names.append(name)
    return sorted(set(names))


def get_collection(name: str):
    """拿 collection（轻量 wrapper，不缓存，避免建删库后失效）。"""
    return get_client().get_or_create_collection(name)


def collection_info(name: str) -> dict:
    """返回 {count, dimension, space}。"""
    col = get_collection(name)
    info = {"count": col.count(), "dimension": None, "space": "l2"}
    if info["count"] > 0:
        try:
            res = col.get(limit=1, include=["embeddings"])
            emb = res.get("embeddings")
            if emb is not None and len(emb) > 0:
                info["dimension"] = int(len(emb[0]))
        except Exception:
            pass
    try:
        meta = col.metadata or {}
        hnsw = meta.get("hnsw", {}) or {}
        info["space"] = hnsw.get("space", "l2")
    except Exception:
        pass
    return info


def create_collection(name: str, space: str = "cosine") -> None:
    """新建库。space: cosine（推荐，相似度语义更直观）或 l2（与旧库一致）。"""
    get_client().create_collection(name, metadata={"hnsw:space": space})


def collection_breakdown(name: str) -> dict:
    """分批拉取全部文档，统计 {total_chars, books:{书名:条数}, files:{文件名:条数}}。

    数据量大时按 1000 条一批拉取，适合数千条级别；对超大库建议只在有需要时调用。
    """
    col = get_collection(name)
    books, files = {}, {}
    total_chars = 0
    offset = 0
    while True:
        res = col.get(limit=1000, offset=offset, include=["documents", "metadatas"])
        ids = res.get("ids") or []
        if not ids:
            break
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        for i, m in enumerate(metas or []):
            m = m or {}
            b = m.get("book") or "(无书名)"
            books[b] = books.get(b, 0) + 1
            f = m.get("filename") or "(无来源)"
            files[f] = files.get(f, 0) + 1
            if i < len(docs or []):
                total_chars += len(docs[i] or "")
        offset += len(ids)
        if len(ids) < 1000:
            break
    return {"total_chars": total_chars, "books": books, "files": files}


def delete_collection(name: str) -> None:
    get_client().delete_collection(name)


def clear_collection(name: str) -> int:
    """清空 collection 全部文档，返回删除条数（分页取 id 删除，适配大库）。"""
    col = get_collection(name)
    removed = 0
    while True:
        res = col.get(limit=1000, include=[])
        ids = list(res.get("ids") or [])
        if not ids:
            break
        col.delete(ids=ids)
        removed += len(ids)
        if len(ids) < 1000:
            break
    return removed
