# -*- coding: utf-8 -*-
"""登录：本地工具的简单密码门。

- 密码存于 `.streamlit/secrets.toml` 的 `[auth] password`。
- 当前已取消密码登录（`LOGIN_REQUIRED = False`），`app.py` 已不再调用本模块。
- 想恢复密码登录：把 `LOGIN_REQUIRED` 改为 `True`，并在 `app.py` 顶部恢复
  `import login` 和 `if not login.require_login(): st.stop()` 两行。
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")

import streamlit as st

LOGIN_REQUIRED = False  # 已取消密码登录（2026-08-17）。改回 True 并恢复 app.py 里的调用即可重新启用


def _expected_password() -> str:
    try:
        return str((st.secrets.get("auth", {}) or {}).get("password", ""))
    except Exception:
        return ""


def require_login() -> bool:
    """未登录则渲染登录页并返回 False；已登录返回 True。"""
    if not LOGIN_REQUIRED:
        st.session_state.authed = True
        return True
    if st.session_state.get("authed"):
        return True
    _render_login()
    return False


def logout() -> None:
    """清空登录状态（侧边栏退出按钮用）。"""
    st.session_state.authed = False
    for k in ("login_pw",):
        st.session_state.pop(k, None)


def _render_login() -> None:
    st.markdown(
        """<style>
        [data-testid="stAppViewContainer"] > .main .block-container { padding-top: 10vh; }
        .login-hero { text-align: center; margin-bottom: .4rem; }
        .login-hero .logo { font-size: 3rem; }
        .login-hero h1 { font-size: 1.5rem; margin: .3rem 0 0; font-weight: 650; }
        .login-hero p { color: #8a8a80; margin-top: .2rem; }
        div[data-testid="stVerticalBlockBorderWrapper"] { padding: 1.6rem 1.3rem; }
        </style>""",
        unsafe_allow_html=True,
    )

    left, mid, right = st.columns([1, 2, 1])
    with mid:
        with st.container(border=True):
            st.markdown(
                """<div class="login-hero">
                    <div class="logo">📚</div>
                    <h1>Chroma 古籍库</h1>
                    <p>本地史料检索与问答</p>
                </div>""",
                unsafe_allow_html=True,
            )
            with st.form("login_form"):
                pw = st.text_input(
                    "访问密码", type="password", placeholder="请输入密码", key="login_pw"
                )
                submitted = st.form_submit_button("进入")
            if submitted:
                expected = _expected_password()
                if not expected:
                    st.error("尚未设置密码：请编辑 .streamlit/secrets.toml 填写 auth.password")
                elif pw == expected:
                    st.session_state.authed = True
                    st.rerun()
                else:
                    st.error("密码不正确，请重试。")
            st.caption("本地工具 · 密码保存在 .streamlit/secrets.toml")
