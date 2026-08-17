# -*- coding: utf-8 -*-
"""全局样式：简洁、克制、带科技感的视觉系统。"""

import streamlit as st

_CSS = """
<style>
/* ===== 基础画布：中性灰阶 + 克制强调色 ===== */
[data-testid="stDecoration"] { display: none; }        /* 去掉顶部渐变装饰条 */
[data-testid="stHeader"] { background: rgba(255, 255, 255, .88); }
footer { visibility: hidden; }                          /* 隐藏默认 footer */
[data-testid="stAppViewContainer"] { background: #f7f8fa; }
[data-testid="stMain"] { background: #f7f8fa; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1420px; }
body, [data-testid="stMarkdownContainer"] { color: #273444; }

/* ===== 标题 ===== */
h1 { font-weight: 700; letter-spacing: -0.025em; margin-bottom: .35rem; color: #172234; }
h2 { font-weight: 600; letter-spacing: -0.005em; margin-top: .4rem; }
h3 { font-weight: 600; }

/* ===== Metric 卡片 ===== */
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, .92);
    border: 1px solid #e2e6eb;
    border-radius: 14px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(32, 36, 43, .05);
}
[data-testid="stMetricValue"] { font-weight: 650; font-size: 1.4rem; }
[data-testid="stMetricLabel"] { font-size: .82rem; color: #697586; }

/* ===== 按钮 ===== */
.stButton > button, .stDownloadButton > button {
    border-radius: 8px;
    border: 1px solid #d6dce4;
    transition: all .15s ease;
    font-weight: 550;
}
.stButton > button:hover, .stDownloadButton > button:hover { border-color: #9aa5b1; color: #3f4b59; box-shadow: 0 0 0 1px rgba(63,75,89,.08); }
.stButton > button[kind="primary"] { box-shadow: 0 1px 2px rgba(51, 97, 140, .25); }
.stButton > button[kind="primary"] { background: #5c6673; border-color: #5c6673; color: #ffffff; }
.stButton > button[kind="primary"]:hover { background: #4d5763; border-color: #4d5763; color: #ffffff; }

/* ===== 输入框 / 下拉 / 滑块 ===== */
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div { border-radius: 9px; background: #ffffff; border-color: #d8dee6; }

/* ===== 折叠面板 ===== */
[data-testid="stExpander"] {
    border: 1px solid #e1e5ea;
    border-radius: 12px;
    background: rgba(255, 255, 255, .72);
    overflow: hidden;
}
[data-testid="stExpander"] summary { font-weight: 550; }

/* ===== 标签页 ===== */
[data-testid="stTabs"] [data-baseweb="tab"] { font-weight: 550; }

/* ===== 侧边栏 ===== */
[data-testid="stSidebar"] {
    background: #f1f3f5;
    border-right: 1px solid #e1e5e9;
}
[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { line-height: 1.6; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: #e1e4e8; color: #303a46; border-radius: 8px; }

/* ===== 说明文字更轻 ===== */
[data-testid="stCaptionContainer"] p,
.stCaption p {
    color: #7b8490;
    font-size: .83rem;
}

/* ===== 分隔线更淡 ===== */
hr { border-color: #e5e8ec; }

/* ===== 表格细边框 ===== */
[data-testid="stDataFrame"] { border: 1px solid #e1e5ea; border-radius: 10px; overflow: hidden; }

/* ===== 状态条圆角 ===== */
[data-testid="stStatusWidget"] { border-radius: 10px; }
</style>
"""


def inject() -> None:
    """注入全局 CSS（放在 st.navigation 之后调用，避免影响主区渲染）。"""
    st.markdown(_CSS, unsafe_allow_html=True)
