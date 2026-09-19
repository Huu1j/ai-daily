"""Hugging Face Daily Papers：社区热度论文。官方 JSON API。"""
import json
import re
from collections import defaultdict

from config import TOP_PAPERS
from fetcher import get

API = "https://huggingface.co/api/daily_papers"
SOURCE_NAME = "Hugging Face Daily Papers"
SOURCE_URL = "https://huggingface.co/papers"


def _authors(paper: dict, limit: int = 4) -> str:
    names = [a.get("name", "") for a in (paper.get("authors") or []) if a.get("name")]
    if not names:
        return ""
    head = ", ".join(names[:limit])
    return head + (f" 等 {len(names)} 人" if len(names) > limit else "")


def _clean(s: str, limit: int = 220) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def fetch(today):
    raw = get(API, timeout=40)
    data = json.loads(raw)
    if not isinstance(data, list):
        return {"name": SOURCE_NAME, "url": SOURCE_URL, "papers": [], "note": "API 返回异常"}

    by_date = defaultdict(list)
    for entry in data:
        p = entry.get("paper") or {}
        pid = p.get("id") or entry.get("id") or ""
        if not pid:
            continue
        date = (p.get("publishedAt") or entry.get("publishedAt") or "")[:10]
        by_date[date].append({
            "id": pid,
            "title": (p.get("title") or entry.get("title") or "").strip(),
            "summary": _clean(p.get("summary") or entry.get("summary") or ""),
            "upvotes": p.get("upvotes") or 0,
            "comments": entry.get("numComments") or 0,
            "authors": _authors(p),
            "org": (p.get("organization") or entry.get("organization") or {}).get("name", "")
                   if isinstance(p.get("organization") or entry.get("organization"), dict) else "",
            "url": f"https://huggingface.co/papers/{pid}",
            "arxiv": f"https://arxiv.org/abs/{pid}",
        })

    if not by_date:
        return {"name": SOURCE_NAME, "url": SOURCE_URL, "papers": [], "note": "无数据"}

    today_str = today.strftime("%Y-%m-%d")
    picked_date = today_str if today_str in by_date else max(k for k in by_date if k)
    papers = sorted(by_date[picked_date], key=lambda x: (-x["upvotes"], -x["comments"]))[:TOP_PAPERS]

    return {
        "name": SOURCE_NAME,
        "url": SOURCE_URL,
        "papers": papers,
        "date": picked_date,
        "stale": picked_date != today_str,
    }
