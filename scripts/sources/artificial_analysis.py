"""Artificial Analysis：模型智能指数 / 价格 / 速度榜单。

官方 API 需要 key，改为解析 leaderboard 页面里的 React Flight(RSC) 数据。
"""
import json
import re

from config import TOP_MODELS
from fetcher import get, FetchError

LEADERBOARD = "https://artificialanalysis.ai/leaderboards/models"
SOURCE_NAME = "Artificial Analysis"
SOURCE_URL = "https://artificialanalysis.ai/"


def _flight_buffer(html: str) -> str:
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', html)
    return "".join(json.loads('"' + c + '"') for c in chunks)


def _walk(node, sink: dict):
    """递归遍历 Flight 数据，收集含 intelligenceIndex 的模型对象。"""
    if isinstance(node, dict):
        if "intelligenceIndex" in node and isinstance(node.get("name"), str):
            sink[node["name"]] = node
        for v in node.values():
            _walk(v, sink)
    elif isinstance(node, list):
        for v in node:
            _walk(v, sink)


def _family(name: str) -> str:
    """把 'Claude Opus 5 (Adaptive Reasoning, Max Effort)' 归一到 'Claude Opus 5'。"""
    return re.split(r"\s*[(\[]", name)[0].strip()


def fetch(today):
    html = get(LEADERBOARD, timeout=60)
    buf = _flight_buffer(html)
    found: dict[str, dict] = {}
    for line in buf.split("\n"):
        i = line.find(":")
        if i <= 0:
            continue
        body = line[i + 1:]
        if not body or body[0] not in "[{":
            continue
        try:
            _walk(json.loads(body), found)
        except Exception:
            continue

    if not found:
        raise FetchError("Artificial Analysis 页面结构变化，未解析出模型数据")

    # 同一模型的不同推理配置只保留最高分的那个
    best: dict[str, dict] = {}
    for name, o in found.items():
        if o.get("deprecated"):
            continue
        idx = o.get("intelligenceIndex")
        if not isinstance(idx, (int, float)):
            continue
        fam = _family(name)
        cur = best.get(fam)
        if cur is None or idx > (cur.get("intelligenceIndex") or -1):
            best[fam] = o

    rows = []
    for fam, o in best.items():
        rows.append({
            "name": o.get("name") or fam,
            "family": fam,
            "creator": o.get("modelCreatorName") or "",
            "intelligence": round(o.get("intelligenceIndex") or 0, 1),
            "price_in": o.get("price1mInputTokens"),
            "price_out": o.get("price1mOutputTokens"),
            "tps": o.get("medianOutputTokensPerSecond"),
            "context": o.get("contextWindowTokens"),
            "open": bool(o.get("isOpenWeights")),
        })
    rows.sort(key=lambda r: -r["intelligence"])

    return {
        "name": SOURCE_NAME,
        "url": SOURCE_URL,
        "models": rows[:TOP_MODELS],
        "all": rows,          # 全量用于与历史快照做对比
        "total_models": len(rows),
    }
