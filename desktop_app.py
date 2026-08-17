# -*- coding: utf-8 -*-
"""历史研究 RAG 检索 —— Windows 一键启动器。

双击桌面快捷方式「Chroma 古籍库」即可使用：

  * 打开程序  → 自动在后台启动本地服务，并在独立窗口里显示应用；
  * 关闭窗口  → 自动停止刚才启动的服务，不会残留后台进程。

说明：
  * 若 8501 端口已有一个实例在跑（比如你之前用 bat 手动开过且没关），本程序会直接复用，
    此时关闭窗口不会停掉那个旧实例，请顺手关掉旧的黑窗口。
  * 出错日志写在同目录 desktop_app.log。
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request
import threading

PORT = 8501
HEALTH_URL = "http://127.0.0.1:%d/_stcore/health" % PORT
APP_URL = "http://localhost:%d" % PORT
BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "desktop_app.log")
PYTHON = sys.executable
APP_ENTRY = os.path.join(getattr(sys, "_MEIPASS", BASE), "app.py")


def _log(*args):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(a) for a in args) + "\n")
    except Exception:
        pass


def _port_in_use(port=PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _server_up(timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as r:
                if r.read().strip() == b"ok":
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _spawn_server():
    """后台启动 Streamlit。若端口已有实例则复用，返回 None。"""
    if _server_up(timeout=4):
        _log("检测到已有服务在运行（端口 %d），直接复用。" % PORT)
        return None
    # PyInstaller 冻结模式下，直接在当前 exe 进程内启动 Streamlit，
    # 避免分发包依赖用户电脑上的 Python。
    if getattr(sys, "frozen", False):
        from streamlit.web import bootstrap

        def run_embedded():
            try:
                bootstrap.run(APP_ENTRY, "", [], {
                    "server.port": PORT,
                    "server.headless": True,
                    "browser.gatherUsageStats": False,
                })
            except Exception as exc:
                _log("内置 Streamlit 服务异常：%r" % (exc,))

        threading.Thread(target=run_embedded, daemon=True, name="streamlit-server").start()
        if not _server_up(timeout=120):
            _log("内置服务启动超时。")
            return None
        _log("内置服务就绪。")
        return None

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        [PYTHON, "-m", "streamlit", "run", APP_ENTRY,
         "--server.port", str(PORT), "--server.headless", "true"],
        cwd=BASE, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    _log("已启动 Streamlit 进程 pid=%s，等待服务就绪…" % proc.pid)
    if not _server_up(timeout=120):
        _log("服务启动超时，尝试结束进程。")
        try:
            proc.kill()
        except Exception:
            pass
        return None
    _log("服务就绪。")
    return proc


def _stop(proc):
    if proc is None:
        return
    _log("停止服务 pid=%s" % proc.pid)
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _show_message(title, text):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, text)
        root.destroy()
    except Exception:
        print(text)


def _fallback_window(proc):
    """pywebview 不可用时的兜底：一个简单的控制小窗（同样“关窗即停服务”）。"""
    try:
        import tkinter as tk
        import webbrowser
    except Exception:
        _stop(proc)
        return
    root = tk.Tk()
    root.title("历史研究 RAG 检索 · 控制")
    root.geometry("360x170")
    root.resizable(False, False)
    tk.Label(root, text="历史研究 RAG 检索", font=("Microsoft YaHei UI", 13, "bold")).pack(pady=(22, 2))
    tk.Label(root, text="本地服务正在运行：%s" % APP_URL, fg="#5C6673").pack()

    def open_ui():
        webbrowser.open(APP_URL)

    tk.Button(root, text="打开界面", width=16, command=open_ui).pack(pady=(14, 2))
    tk.Button(root, text="退出（同时停止服务）", width=16, command=root.destroy).pack()
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
    _stop(proc)


def main():
    _log("===== Chroma 桌面版启动 =====")
    proc = _spawn_server()
    if proc is None and not _port_in_use(PORT):
        _show_message("启动失败", "Chroma 服务启动失败，请查看 %s 了解详情。" % LOG)
        return

    try:
        import webview  # 内嵌窗口（基于系统 WebView2）
    except Exception:
        webview = None
        _log("pywebview 不可用，使用兜底控制窗口。")

    if webview is not None:
        try:
            webview.create_window(
                "历史研究 RAG 检索",
                APP_URL,
                width=1240, height=840,
                min_size=(920, 640),
            )
            webview.start()
        except Exception as e:
            _log("内嵌窗口启动失败：%r，改用控制窗口。" % e)
            _fallback_window(proc)
            return
        _stop(proc)  # 关窗即停
    else:
        _fallback_window(proc)


if __name__ == "__main__":
    main()
