# -*- coding: utf-8 -*-
"""导入层（纯函数，可独立测试）：文件过滤、md 按 ## 切片、metadata/id 生成、幂等去重。"""
import hashlib
import os
import re
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

_OB_CITE = re.compile(r"\[\[#?([^\]|]+)(?:\|[^\]]*)?\]\]")


# ---------- 文件过滤 ----------
def scan_folder(folder: str, include_report: bool = False):
    """扫描文件夹，返回 (included, excluded)。

    included: 可导入的 .md 文件（含 size_kb）。
    excluded: 被跳过的 [(name, reason), ...]，reason 说明跳过原因，便于界面展示。
    """
    included, excluded = [], []
    if not folder or not os.path.isdir(folder):
        return included, excluded
    for root, dirs, files in os.walk(folder):
        skipped_dirs = [d for d in dirs if d.endswith("_assets")]
        for d in skipped_dirs:
            excluded.append((os.path.join(root, d) + "\\", "目录名以 _assets 结尾（图片/附件目录）"))
        dirs[:] = [d for d in dirs if not d.endswith("_assets")]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            reason = ""
            if ".bak_" in fn:
                reason = "备份文件（文件名含 .bak_）"
            elif fn.endswith("校对报告.md") and not include_report:
                reason = "校对报告（未勾选「包含校对报告」）"
            if reason:
                excluded.append((os.path.join(root, fn), reason))
                continue
            full = os.path.join(root, fn)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            included.append(
                {"path": os.path.normpath(full), "name": fn, "size_kb": size // 1024}
            )
    included.sort(key=lambda d: d["name"])
    excluded.sort(key=lambda x: x[0])
    return included, excluded


def list_candidate_md(folder: str, include_report: bool = False) -> list:
    """返回 folder 下合法 .md 文件；跳过备份/校对报告/_assets 目录。"""
    included, _ = scan_folder(folder, include_report=include_report)
    return included


# ---------- md 解析与切片 ----------
def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def slice_md_by_heading(text: str):
    """返回 (book_title, [(chapter, body, idx), ...])。

    只切 `## ` 二级标题（正史卷标题）；`# 书名` 只取书名；`## 目录` 整章跳过；
    无任何 `## ` 时整文件作为一章兜底。
    """
    text = text.lstrip("﻿").replace("\r\n", "\n")
    lines = text.split("\n")

    book_title = None
    for line in lines:
        s = line.strip()
        if s.startswith("# "):
            book_title = s[2:].strip()
            break

    chapters = []
    cur_title = None
    cur_lines = []
    seq = 0
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            if cur_title is not None and "\n".join(cur_lines).strip():
                chapters.append((cur_title, "\n".join(cur_lines).strip(), seq))
            cur_title = s[3:].strip()
            cur_lines = []
            seq += 1
        else:
            cur_lines.append(line)
    if cur_title is not None and "\n".join(cur_lines).strip():
        chapters.append((cur_title, "\n".join(cur_lines).strip(), seq))

    chapters = [c for c in chapters if c[0] != "目录"]

    if not chapters and text.strip():
        chapters = [(book_title or "全文", text.strip(), 0)]

    return book_title, chapters


def split_long_chunk(text: str, max_chars: int, overlap: int = 50) -> list:
    """超长章节按段落/句号拆子段，尽量不截断句子。"""
    if len(text) <= max_chars:
        return [text]
    paras = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        while len(p) > max_chars:
            cut = p.rfind("。", 0, max_chars)
            if cut < max_chars // 2:
                cut = p.rfind("，", 0, max_chars)
            if cut < max_chars // 2:
                cut = max_chars
            piece = p[: cut + 1]
            if cur:
                chunks.append(cur)
            chunks.append(piece)
            p = p[cut + 1 - overlap :]
        if len(cur) + len(p) <= max_chars:
            cur = (cur + p) if cur else p
        else:
            chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c.strip()]


def slice_for_import(text: str, mode: str, max_chars: int):
    """按策略返回 [(chapter, body, sub_idx), ...]（chapter 为标题或子块名）。"""
    book, chapters = slice_md_by_heading(text)
    records = []
    if mode == "whole":
        if text.strip():
            records.append(((book or "全文"), text.strip(), 0))
        return book, records
    for title, body, idx in chapters:
        if mode == "heading":
            records.append((title, body, 0))
        else:  # "split"
            sub_count = 0
            for seg in split_long_chunk(body, max_chars):
                sub_name = title if sub_count == 0 else f"{title}（续{sub_count}）"
                records.append((sub_name, seg, sub_count))
                sub_count += 1
    return book, records


# ---------- metadata 与 id ----------
def make_id(filename: str, chapter: str, sub: int) -> str:
    raw = f"{filename}::{chapter}::{sub}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


def build_metadata(filename: str, path: str, book: str, chapter: str, sub: int, text: str) -> dict:
    return {
        "book": book or "",
        "filename": filename,
        "path": path,
        "chapter": chapter,
        "chapter_idx": sub,
        "char_count": len(text),
        "imported_at": datetime.now().isoformat(timespec="seconds"),
        "file_mtime": None,
    }
