"""摘要生成。

rule 模式（默认）：直接采用源站提供的标题与摘要原文，零成本、零依赖。
llm 模式：调用 OpenAI 兼容接口，把标题/摘要改写成中文一句话摘要。
        开启方式：SUMMARY_MODE=llm + LLM_API_KEY（可选 LLM_BASE_URL / LLM_MODEL）。
        同一个 URL 的摘要会缓存在 data/summary_cache.json，避免重复计费。
"""
import json
import os
import re
import urllib.error
import urllib.request

from config import (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, SUMMARY_MODE,
                    DATA_DIR)

CACHE_PATH = os.path.join(DATA_DIR, "summary_cache.json")
MAX_CHARS = 900


def _load_cache() -> dict:
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)


def enabled() -> bool:
    return SUMMARY_MODE == "llm" and bool(LLM_API_KEY)


def _call_llm(prompt: str, timeout: int = 60) -> str:
    url = LLM_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "你是技术资讯编辑。把给定的英文标题与摘要压缩成一句中文摘要，"
                                          "控制在 60 字以内，保留模型名/机构名等专有名词原文，不要臆造事实。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 220,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {LLM_API_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", "ignore"))
    return data["choices"][0]["message"]["content"].strip()


def summarize_one(title: str, summary: str) -> str | None:
    """返回中文一句话摘要；未启用 LLM 或失败时返回 None（调用方回退到原文）。"""
    if not enabled():
        return None
    key = re.sub(r"\s+", " ", (title or ""))[:200]
    cache = _load_cache()
    if key in cache:
        return cache[key] or None
    try:
        text = _call_llm(f"标题：{title}\n\n摘要：{(summary or '')[:MAX_CHARS]}")
        text = re.sub(r"\s+", " ", text).strip()
        cache[key] = text
        _save_cache(cache)
        return text
    except Exception:
        return None
