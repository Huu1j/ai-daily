"""AINews (news.smol.ai)：工作日 AI 工程要闻速览。官方 RSS 含全文。"""
import re

from config import LOOKBACK_DAYS, SMOL_ITEMS
from fetcher import get
from rss import parse_rss

FEED = "https://news.smol.ai/rss.xml"
SOURCE_NAME = "AINews (smol.ai)"
SOURCE_URL = "https://news.smol.ai/"


def _paragraphs(text: str, limit: int = 5, per_len: int = 260) -> list[str]:
    """把一期长文切成要点段落。优先按 markdown 标题切，否则按空行/句号切。"""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # 去掉 markdown 链接语法
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if len(c.strip()) > 40]
    if len(chunks) < 2:
        chunks = [c.strip() for c in re.split(r"(?<=[.!?。])\s+", text) if len(c.strip()) > 40]
    out = []
    for c in chunks[:limit]:
        c = re.sub(r"\s+", " ", c).strip()
        out.append(c[:per_len] + ("…" if len(c) > per_len else ""))
    return out


def fetch(today):
    items = parse_rss(get(FEED, timeout=45))
    if not items:
        return {"name": SOURCE_NAME, "url": SOURCE_URL, "issues": [], "note": "RSS 为空"}

    cutoff = today.timestamp() - LOOKBACK_DAYS * 86400
    fresh = []
    for it in items:
        ts = it["pubdate"].timestamp() if it["pubdate"] else None
        if ts and ts >= cutoff:
            fresh.append(it)

    # 站点停更/周末时窗口内没有内容 —— 回退到最新一期，并标注发布日期
    stale = False
    if fresh:
        picked = fresh[:SMOL_ITEMS]
    else:
        picked = items[:SMOL_ITEMS]
        stale = bool(items)

    issues = []
    for it in picked:
        issues.append({
            "title": it["title"],
            "url": it["link"],
            "date": it["pubdate"].strftime("%Y-%m-%d") if it["pubdate"] else "",
            "points": _paragraphs(it["description"]),
        })

    return {
        "name": SOURCE_NAME,
        "url": SOURCE_URL,
        "issues": issues,
        "stale": stale,
        "latest_date": issues[0]["date"] if issues else "",
    }
