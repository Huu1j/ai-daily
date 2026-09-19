"""极简 RSS 2.0 / Atom 解析。返回统一的 item 字典列表。"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"


def _text(node) -> str:
    return (node.text or "").strip()


def _clean(s: str) -> str:
    """去掉 HTML 标签，压缩空白。"""
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
          .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
          .replace("&apos;", "'"))
    return re.sub(r"\s+", " ", s).strip()


def parse_pubdate(value: str):
    """尽力把各种日期字符串转成 datetime（tz-aware，UTC）。"""
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc))
        except ValueError:
            continue
    return None


def parse_rss(xml: str) -> list[dict]:
    """解析 RSS2.0 或 Atom，返回 [{title, link, pubdate, description, guid}]。"""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        # 有些 feed 带非法字符，退化成正则兜底
        return _parse_fallback(xml)

    items = []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        rec = {"title": "", "link": "", "pubdate": None, "description": "", "guid": ""}
        for child in node:
            ctag = child.tag.split("}")[-1]
            if ctag == "title":
                rec["title"] = _clean(_text(child))
            elif ctag == "link":
                href = child.attrib.get("href") or _text(child)
                if href and not rec["link"]:
                    rec["link"] = href.strip()
            elif ctag in ("pubDate", "published", "updated", "date", "dc:date"):
                rec["pubdate"] = rec["pubdate"] or parse_pubdate(_text(child))
            elif ctag == "description" or ctag == "summary":
                rec["description"] = rec["description"] or _clean(_text(child) or "".join(child.itertext()))
            elif ctag == "encoded" and child.tag == CONTENT_NS + "encoded":
                rec["description"] = rec["description"] or _clean(_text(child))
            elif ctag == "guid" or ctag == "id":
                rec["guid"] = _text(child)
        if rec["title"] or rec["link"]:
            items.append(rec)
    return items


def _parse_fallback(xml: str) -> list[dict]:
    items = []
    for block in re.findall(r"<item[\s>][\s\S]*?</item>", xml):
        title = re.search(r"<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</title>", block)
        link = re.search(r"<link>([\s\S]*?)</link>", block)
        date = re.search(r"<pubDate>([\s\S]*?)</pubDate>", block)
        desc = re.search(r"<description>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?</description>", block)
        items.append({
            "title": _clean(title.group(1)) if title else "",
            "link": (link.group(1).strip() if link else ""),
            "pubdate": parse_pubdate(date.group(1)) if date else None,
            "description": _clean(desc.group(1)) if desc else "",
            "guid": "",
        })
    return items
