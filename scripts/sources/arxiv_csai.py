"""arXiv cs.AI 最新预印本。

用官方 API 而不是 RSS：RSS 只在工作日推送，周末会返回空 channel，
导致日报缺一大块。API 可以按提交时间倒序稳定取到最新条目。
"""
import re

from config import TOP_ARXIV
from fetcher import get
from rss import parse_rss

FEED = ("http://export.arxiv.org/api/query?search_query=cat:cs.AI"
        "&start=0&max_results=40&sortBy=submittedDate&sortOrder=descending")
SOURCE_NAME = "arXiv cs.AI"
SOURCE_URL = "https://arxiv.org/list/cs.AI/recent"


def _split_desc(desc: str) -> tuple[str, str]:
    """arXiv 的 description 形如 'Authors: ... Abstract: ...'，拆出作者与摘要。"""
    authors, abstract = "", desc
    m = re.search(r"Authors:\s*(.*?)(?:\bAbstract\s*:)", desc, re.S)
    if m:
        authors = re.sub(r"\s+", " ", m.group(1)).strip()
        abstract = desc[m.end():]
    else:
        m2 = re.search(r"\bAbstract\s*:\s*(.*)$", desc, re.S)
        if m2:
            abstract = m2.group(1)
    abstract = re.sub(r"\s+", " ", abstract).strip()
    return authors, abstract[:240] + ("…" if len(abstract) > 240 else "")


def fetch(today):
    items = parse_rss(get(FEED, timeout=45))
    if not items:
        items = parse_rss(get("http://export.arxiv.org/rss/cs.AI", timeout=45))
    entries = []
    for it in items:
        link = it["link"] or ""
        m = re.search(r"abs/([0-9]{4}\.[0-9]{4,5})", link)
        arxiv_id = m.group(1) if m else ""
        title = re.sub(r"\s+", " ", it["title"]).strip()
        # arXiv RSS 标题末尾常带 "(arXiv:XXXX.XXXXX [cs.AI])"
        title = re.sub(r"\s*\(arXiv:[^)]*\)\s*$", "", title)
        authors, abstract = _split_desc(it["description"])
        if not title:
            continue
        entries.append({
            "id": arxiv_id,
            "title": title,
            "authors": authors,
            "summary": abstract,
            "url": link or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else SOURCE_URL),
            "date": it["pubdate"].strftime("%Y-%m-%d") if it["pubdate"] else "",
        })

    entries = [e for e in entries if e["id"]][:TOP_ARXIV]
    dates = [e["date"] for e in entries if e["date"]]
    return {
        "name": SOURCE_NAME,
        "url": SOURCE_URL,
        "papers": entries,
        "date": max(dates) if dates else "",
        "total": len(entries),
    }
