"""把最新一期日报渲染成单页 HTML，供本地预览。

不是博客的组成部分（Jekyll 会用 _layouts 自己渲染），纯粹是为了在本机一眼看到成品效果。
用法：python scripts/preview.py [输出路径]
"""
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import POSTS_DIR, ROOT  # noqa: E402


def inline(text: str) -> str:
    """行内标记：加粗、链接、代码。已含 HTML 标签的片段保持原样。"""
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


def md_to_html(md: str) -> str:
    # 去掉 Jekyll front matter
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end != -1:
            md = md[end + 4:]

    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        # 表格
        if line.lstrip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            rows = [[c.strip() for c in r.strip("|").split("|")] for r in block]
            rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
            if rows:
                out.append("<table>")
                out.append("<tr>" + "".join(f"<th>{inline(html.unescape(c))}</th>" for c in rows[0]) + "</tr>")
                for r in rows[1:]:
                    out.append("<tr>" + "".join(f"<td>{inline(html.unescape(c))}</td>" for c in r) + "</tr>")
                out.append("</table>")
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            lv = len(m.group(1))
            out.append(f"<h{lv}>{inline(m.group(2))}</h{lv}>")
            i += 1
            continue

        # 引用
        if line.startswith(">"):
            out.append(f"<blockquote>{inline(line.lstrip('> '))}</blockquote>")
            i += 1
            continue

        # 列表
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(t)}</li>" for t in items) + "</ul>")
            continue

        # 含 HTML 标签的行（如 meta-line）原样输出
        if re.search(r"<(span|div|p|br)[ >]", line):
            out.append(line)
            i += 1
            continue

        out.append(f"<p>{inline(line)}</p>")
        i += 1

    return "\n".join(out)


def latest_post() -> tuple[str, str]:
    files = sorted(f for f in os.listdir(POSTS_DIR) if f.endswith(".md"))
    if not files:
        raise SystemExit("还没有生成任何日报，先跑 python scripts/main.py")
    path = os.path.join(POSTS_DIR, files[-1])
    with open(path, encoding="utf-8") as f:
        return files[-1][:-3], f.read()


def build() -> str:
    name, md = latest_post()
    css_path = os.path.join(ROOT, "assets", "css", "style.css")
    try:
        with open(css_path, encoding="utf-8") as f:
            css = f.read()
    except OSError:
        css = ""
    body = md_to_html(md)
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 日报 · {name}（本地预览）</title>
<style>{css}
body{{background:#fff}}
.preview-tip{{background:#fff7e6;border:1px solid #ffd591;padding:8px 14px;font-size:13px;margin:14px 0;border-radius:4px}}
</style></head>
<body>
<header class="site-header"><div class="wrap">
<a class="site-title" href="#">AI 日报</a>
<span class="site-desc">每日自动聚合 —— AI 要闻 / 前沿论文 / 模型榜单</span>
</div></header>
<main class="wrap site-main">
<div class="preview-tip">本地预览效果（由 scripts/preview.py 生成）。推送到 GitHub 后，实际页面由 Jekyll 用 _layouts/post.html 渲染，样式一致。</div>
{body}
</main>
<footer class="site-footer"><div class="wrap"><p>由 GitHub Actions 每日自动抓取生成</p></div></footer>
</body></html>"""


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "preview.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(build())
    print(f"预览已生成：{out}")
