"""alphaXiv：论文阅读与解读社区。

站点是纯客户端渲染，服务端 HTML 里没有任何论文数据，常规抓取拿不到内容。
因此默认策略是「链接增强」：给每篇 arXiv/HF 论文附上 alphaXiv 直达链接，
点进去即可看解读、笔记与讨论，零抓取成本。

如果你确实想抓取它的首页/趋势列表，设置环境变量 ALPHAXIV_BROWSER=1，
并在运行环境安装 playwright（pip install playwright && playwright install chromium）。
"""
from config import ALPHAXIV_BROWSER

SOURCE_NAME = "alphaXiv"
SOURCE_URL = "https://www.alphaxiv.org/"


def abs_url(arxiv_id: str) -> str:
    """论文的 alphaXiv 直达链接。"""
    return f"https://www.alphaxiv.org/abs/{arxiv_id}" if arxiv_id else SOURCE_URL


def overview_url(arxiv_id: str) -> str:
    return f"https://www.alphaxiv.org/overview/{arxiv_id}" if arxiv_id else SOURCE_URL


def _fetch_with_browser(limit: int = 10):
    """可选：用无头浏览器渲染后抓取首页论文条目。失败返回空列表。"""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        return []

    items = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            page = browser.new_page()
            page.goto(SOURCE_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(3000)
            anchors = page.eval_on_selector_all(
                "a[href*='/abs/'], a[href*='/overview/']",
                "els => els.map(e => ({href: e.href, text: (e.innerText||'').trim()}))",
            )
            seen = set()
            for a in anchors:
                href, text = a.get("href", ""), a.get("text", "")
                if not text or len(text) < 15 or href in seen:
                    continue
                seen.add(href)
                items.append({"title": text.split("\n")[0][:160], "url": href})
                if len(items) >= limit:
                    break
            browser.close()
    except Exception:
        return []
    return items


def fetch(today):
    items = _fetch_with_browser() if ALPHAXIV_BROWSER else []
    return {
        "name": SOURCE_NAME,
        "url": SOURCE_URL,
        "items": items,
        "mode": "browser" if ALPHAXIV_BROWSER else "link",
        "note": "" if ALPHAXIV_BROWSER else "纯前端渲染站点，本期以论文直达链接形式呈现",
    }
