# -*- coding: utf-8 -*-
"""LLM 后端：配置持久化（config.json）+ OpenAI 兼容 chat/completions 调用。

支持两种后端（都走 OpenAI 兼容接口，可接任意厂商）：
- 自建 vLLM / 开源模型（本地或任意云主机的 base_url）
- 云 API 服务（OpenAI / DeepSeek / 智谱 等，填 api_key）
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

import requests

APP_DIR = os.path.dirname(os.path.abspath(__file__))
USER_CONFIG_DIR = os.environ.get(
    "HISTORY_RAG_CONFIG_DIR",
    os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "HistoricalResearchRAG"),
)
os.makedirs(USER_CONFIG_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(USER_CONFIG_DIR, "config.json")
LEGACY_CONFIG_PATH = os.path.join(APP_DIR, "config.json")

DEFAULT_CONFIG = {
    "backend_mode": "vllm",          # "vllm" | "apikey"
    "vllm": {
        "base_url": "http://localhost:8000/v1",
        "api_key": "EMPTY",
        "model": "Qwen3-8B",
        "temperature": 0.7,
    },
    "apikey": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
    },
}


def load_config() -> dict:
    """读取 config.json；不存在则写入默认并返回。"""
    source_path = CONFIG_PATH if os.path.exists(CONFIG_PATH) else LEGACY_CONFIG_PATH
    if os.path.exists(source_path):
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 补缺省键（老配置文件升级）
            for section in ("vllm", "apikey"):
                if section not in data:
                    data[section] = dict(DEFAULT_CONFIG[section])
                else:
                    for k, v in DEFAULT_CONFIG[section].items():
                        data[section].setdefault(k, v)
            data.setdefault("backend_mode", "vllm")
            return data
        except Exception:
            pass
    data = json.loads(json.dumps(DEFAULT_CONFIG))
    save_config(data)
    return data


def save_config(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def active_backend(cfg: dict) -> dict:
    """返回当前生效的后端配置（合并 backend_mode）。"""
    mode = cfg.get("backend_mode", "vllm")
    backend = dict(cfg.get(mode, {}) or {})
    # 密钥只从环境变量读取，避免被写入 config.json、版本库或备份文件。
    env_key = "CHROMA_LLM_API_KEY" if mode == "apikey" else "CHROMA_VLLM_API_KEY"
    backend["api_key"] = os.environ.get(env_key, "")
    return backend


def chat(cfg: dict, messages: list, timeout: int = 120) -> str:
    """调用 OpenAI 兼容 chat/completions，返回回复文本。"""
    backend = active_backend(cfg)
    base_url = (backend.get("base_url") or "").rstrip("/")
    api_key = backend.get("api_key", "") or "EMPTY"
    model = backend.get("model", "")
    temperature = float(backend.get("temperature", 0.7))

    url = base_url + "/chat/completions"
    if not base_url:
        raise RuntimeError("未配置 base_url，请先在 LLM 设置里填写。")
    if not model:
        raise RuntimeError("未配置 model 名称，请先在 LLM 设置里填写。")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(f"无法连接 LLM 后端 {url}：{e}") from e
    except requests.exceptions.Timeout as e:
        raise RuntimeError(f"LLM 请求超时（{timeout}s）：{e}") from e

    if resp.status_code != 200:
        raise RuntimeError(
            f"LLM 返回 HTTP {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"LLM 响应格式异常：{e} — {str(data)[:200]}") from e


def build_rag_messages(system_prompt: str, context: str, question: str) -> list:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context + "\n\n问题：" + question},
    ]
