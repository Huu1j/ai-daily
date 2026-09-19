"""The Batch (DeepLearning.AI) 周报。站点无 RSS，改为解析 SSR 页面 + sitemap。"""
import html
import re

from config import BATCH_ARTICLES
from fetcher import get

INDEX = "https://www.deeplearning.ai/the-batch"
SITEMAP = "https://www.deeplearning.ai/sitemap.xml"
SOURCE_NAME = "The Batch"
SOURCE_URL = "https://www.deeplearning.ai/the-batch"

# 页面里这些 h1 是栏目分节名，不是文章标题
SECTIONS = {
    "news", "data points", "research", "business", "science", "culture",
    "hardware", "ai careers", "letters", "opinion", "calendar", "podcasts",
}


def _strip(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _sitemap_slugs() -> dict[str, str]:
    """备用：从 sitemap 拿 {slug: URL}。

    注意 sitemap 通常滞后一期，最新一期的文章还没进来，
    所以主路径用的是 h1 自带的 id（见 fetch），这里只做兜底。
    """
    try:
        xml = get(SITEMAP, timeout=40)
    except Exception:
        return {}
    out = {}
    for slug in re.findall(r"<loc>https://www\.deeplearning\.ai/the-batch/([^<]+)</loc>", xml):
        if not slug or slug.startswith(("tag/", "issue-", "about", "search")):
            continue
        out[slug] = f"https://www.deeplearning.ai/the-batch/{slug}"
    return out


def fetch(today):
    index_html = get(INDEX, timeout=40)
    issue_nums = [int(n) for n in re.findall(r'href="/the-batch/issue-(\d+)"', index_html)]
    if not issue_nums:
        return {"name": SOURCE_NAME, "url": SOURCE_URL, "articles": [], "note": "未找到 issue 链接"}

    issue_no = max(issue_nums)
    issue_url = f"https://www.deeplearning.ai/the-batch/issue-{issue_no}"
    page = get(issue_url, timeout=40)

    m = re.search(r'href="/the-batch/tag/([a-z]{3}-\d{2}-\d{4})"', page)
    date_raw = m.group(1) if m else ""
    try:
        from datetime import datetime
        date = datetime.strptime(date_raw, "%b-%d-%Y").strftime("%Y-%m-%d") if date_raw else ""
    except ValueError:
        date = ""

    # 首页卡片上的期号标题与摘要
    headline, blurb = "", ""
    card = re.search(
        rf'href="/the-batch/issue-{issue_no}"[^>]*aria-label="([^"]+)"', index_html)
    if card:
        headline = _strip(card.group(1))
    if not headline:
        card2 = re.search(
            rf'<a class="absolute inset-0" aria-label="([^"]+)" href="/the-batch/issue-{issue_no}"', index_html)
        headline = _strip(card2.group(1)) if card2 else f"Issue {issue_no}"

    slugs = _sitemap_slugs()
    articles = []
    seen = set()
    for m in re.finditer(r"<h1([^>]*)>([\s\S]*?)</h1>", page):
        attrs, title = m.group(1), _strip(m.group(2))
        if not title or title.lower() in SECTIONS or len(title) < 10:
            continue
        if title.lower() in seen:
            continue
        seen.add(title.lower())
        # 优先用 h1 自带的 id 拼独立文章页；没有 id 再查 sitemap；都没有就退回本期主页
        anchor = re.search(r'id="([^"]+)"', attrs)
        slug = anchor.group(1) if anchor else _slugify(title)
        if anchor:
            url = f"https://www.deeplearning.ai/the-batch/{slug}"
        elif slug in slugs:
            url = slugs[slug]
        else:
            url = issue_url
        articles.append({"title": title, "url": url})
        if len(articles) >= BATCH_ARTICLES:
            break

    return {
        "name": SOURCE_NAME,
        "url": SOURCE_URL,
        "issue": issue_no,
        "issue_url": issue_url,
        "headline": headline,
        "blurb": blurb,
        "date": date,
        "articles": articles,
    }
