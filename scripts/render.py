"""把各源结果渲染成 Jekyll 日报 Markdown，并写出结构化归档。"""
import json
import os
import re

from config import DATA_DIR, POSTS_DIR, ROOT
from sources import alphaxiv

# Jekyll 会把 {{ }} 当 Liquid 解析，正文里出现会渲染失败
_LIQUID_RE = re.compile(r"(\{\{|\{%|\{#)")


def esc(text: str) -> str:
    if not text:
        return ""
    return _LIQUID_RE.sub(lambda m: m.group(1).replace("{", "&#123;"), str(text))


def _num(v, nd=0, suffix=""):
    if v is None:
        return "—"
    try:
        if nd == 0:
            return f"{int(round(v))}{suffix}"
        return f"{round(float(v), nd)}{suffix}"
    except (TypeError, ValueError):
        return "—"


def _ctx(v):
    if not v:
        return "—"
    v = int(v)
    if v >= 1_000_000:
        return f"{v // 1_000_000}M"
    return f"{v // 1000}K" if v >= 1000 else str(v)


# ── 各区块 ────────────────────────────────────────────────

def render_smol(block: dict) -> list[str]:
    lines = []
    if not block.get("issues"):
        return ["_本期未获取到内容。_"]
    if block.get("stale"):
        lines.append(f"> 源站最新一期发布于 {block.get('latest_date') or '未知'}，超过回看窗口，此处按最新一期呈现。")
    for issue in block["issues"]:
        title = esc(issue["title"])
        url = issue["url"]
        date = issue["date"] or "日期未知"
        lines.append(f"### [{title}]({url})\n")
        lines.append(f"<span class=\"meta-line\">发布日期：{date} · 来源：AINews</span>\n")
        if issue["points"]:
            for p in issue["points"]:
                lines.append(f"- {esc(p)}")
        lines.append("")
    return lines


def render_batch(block: dict) -> list[str]:
    if not block.get("articles") and not block.get("headline"):
        return ["_本期未获取到内容。_"]
    lines = []
    issue_no = block.get("issue")
    date = block.get("date") or "日期未知"
    link = block.get("issue_url") or "https://www.deeplearning.ai/the-batch"
    headline = esc(block.get("headline") or f"Issue {issue_no}")
    lines.append(f"**第 {issue_no} 期 · {date}** —— [{headline}]({link})\n")
    if block.get("articles"):
        for a in block["articles"]:
            lines.append(f"- [{esc(a['title'])}]({a['url']})")
    else:
        lines.append("_未解析到该期文章列表，直接查看本期主页。_")
    lines.append("")
    return lines


def render_papers(papers: list[dict], date: str, empty_text: str) -> list[str]:
    if not papers:
        return [empty_text]
    lines = []
    if date:
        lines.append(f"<span class=\"meta-line\">论文日期：{date}</span>\n")
    for p in papers:
        title = esc(p["title"])
        links = [f"[HF]({p['url']})"] if "huggingface.co" in p.get("url", "") else []
        if p.get("id"):
            links.append(f"[arXiv](https://arxiv.org/abs/{p['id']})")
            links.append(f"[alphaXiv]({alphaxiv.abs_url(p['id'])})")
        meta = []
        if p.get("upvotes"):
            meta.append(f"👍 {p['upvotes']}")
        if p.get("comments"):
            meta.append(f"💬 {p['comments']}")
        if p.get("authors"):
            meta.append(esc(p["authors"]))
        lines.append(f"- **[{title}]({p.get('url')})**")
        sub = " · ".join(meta)
        if sub:
            lines.append(f"  <span class=\"meta-line\">{sub}</span>")
        if p.get("zh"):
            lines.append(f"  摘要：{esc(p['zh'])}")
        elif p.get("summary"):
            lines.append(f"  摘要：{esc(p['summary'])}")
        lines.append(f"  {' · '.join(links)}")
        lines.append("")
    return lines


def render_models(block: dict, diff: dict) -> list[str]:
    models = block.get("models") or []
    if not models:
        return ["_本期未获取到榜单数据。_"]
    lines = []
    lines.append("| # | 模型 | 厂商 | 智能指数 | 输入 $/M | 输出 $/M | 速度 tok/s | 上下文 | 开源 |")
    lines.append("|---|------|------|---------|---------|---------|-----------|--------|------|")
    for i, m in enumerate(models, 1):
        lines.append(
            f"| {i} | {esc(m['name'])} | {esc(m['creator'])} | {m['intelligence']} | "
            f"{_num(m.get('price_in'), 2)} | {_num(m.get('price_out'), 2)} | "
            f"{_num(m.get('tps'), 1)} | {_ctx(m.get('context'))} | {'✅' if m['open'] else '—'} |"
        )
    lines.append("")
    if block.get("total_models"):
        lines.append(f"<span class=\"meta-line\">本期共收录 {block['total_models']} 个模型族，上表为智能指数前 {len(models)} 名。</span>\n")

    if diff.get("new"):
        lines.append("**新进入榜单的模型**\n")
        for m in diff["new"][:10]:
            lines.append(f"- {esc(m['family'])}（{esc(m['creator'])}）· 智能指数 {m['intelligence']}")
        lines.append("")
    if diff.get("moved"):
        lines.append("**智能指数变化（≥1 分）**\n")
        for m in diff["moved"][:10]:
            arrow = "↑" if m["delta"] > 0 else "↓"
            lines.append(f"- {esc(m['family'])}：{m['old']} → {m['new']} {arrow}{abs(m['delta'])}")
        lines.append("")
    if diff.get("is_first"):
        lines.append("<span class=\"meta-line\">首次记录榜单快照，下期开始显示变化对比。</span>\n")
    return lines


def render_alphaxiv(block: dict) -> list[str]:
    if block.get("items"):
        return [f"- [{esc(i['title'])}]({i['url']})" for i in block["items"]]
    return [
        "alphaXiv 站点为纯前端渲染，服务端取不到列表数据，因此不硬抓。",
        "上面每篇论文都已附带 **alphaXiv 直达链接**，点击即可进入该论文的解读与讨论页。",
        "如需自动抓取其首页趋势列表，可开启浏览器渲染模式（见仓库 README）。",
    ]


# ── 组装 ──────────────────────────────────────────────────

def build_markdown(ctx: dict) -> str:
    date = ctx["date"]
    blocks = ctx["blocks"]
    stats = ctx["stats"]

    out = [
        "---",
        "layout: post",
        f"title: \"AI 日报 · {date}\"",
        f"date: {date} 08:00:00 +0800",
        "categories: [AI日报]",
        # 源名里可能有空格和括号，逐个加引号，避免 YAML 流序列解析出错
        "tags: [" + ", ".join(f'"{s}"' for s in ctx["ok_sources"]) + "]",
        f"stats_summary: \"{stats}\"",
        "---",
        "",
        f"> 本期由 GitHub Actions 自动生成，覆盖 {len(ctx['ok_sources'])} 个信息源："
        f"{'、'.join(ctx['ok_sources']) or '（无）'}。",
        "",
    ]

    out.append("## 一、AI 要闻速览 · AINews (smol.ai)\n")
    out += render_smol(blocks.get("smolai") or {})
    out.append("")

    out.append("## 二、The Batch 周报 · DeepLearning.AI\n")
    out += render_batch(blocks.get("the_batch") or {})
    out.append("")

    out.append("## 三、Hugging Face 热门论文\n")
    out += render_papers((blocks.get("hf_papers") or {}).get("papers", []),
                         (blocks.get("hf_papers") or {}).get("date", ""),
                         "_本期未获取到内容。_")
    out.append("")

    out.append("## 四、arXiv cs.AI 最新论文\n")
    out += render_papers((blocks.get("arxiv") or {}).get("papers", []),
                         (blocks.get("arxiv") or {}).get("date", ""),
                         "_本期未获取到内容。_")
    out.append("")

    out.append("## 五、模型榜单 · Artificial Analysis\n")
    out += render_models(blocks.get("artificial_analysis") or {}, ctx.get("models_diff") or {})
    out.append("")

    out.append("## 六、alphaXiv\n")
    out += render_alphaxiv(blocks.get("alphaxiv") or {})
    out.append("")

    out.append("## 本期统计\n")
    out.append("| 信息源 | 状态 | 条目数 |")
    out.append("|---|---|---|")
    for row in ctx["source_rows"]:
        out.append(f"| {row['name']} | {row['status']} | {row['count']} |")
    out.append("")
    if ctx["failed"]:
        out.append(f"<span class=\"meta-line\">抓取失败：{'、'.join(ctx['failed'])}（已跳过，不影响其他源）</span>\n")

    return "\n".join(out) + "\n"


def write_outputs(ctx: dict) -> tuple[str, str]:
    """写 _posts 日报 + data 归档，返回 (post_path, data_path)。"""
    os.makedirs(POSTS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    date = ctx["date"]

    post_path = os.path.join(POSTS_DIR, f"{date}-ai-daily.md")
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(build_markdown(ctx))

    data_path = os.path.join(DATA_DIR, f"{date}.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(ctx["raw"], f, ensure_ascii=False, indent=1)

    _update_index(date, ctx)
    return post_path, data_path


def _update_index(date: str, ctx: dict) -> None:
    idx_path = os.path.join(DATA_DIR, "index.json")
    try:
        with open(idx_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    except Exception:
        index = {"days": []}
    entry = {"date": date, "stats": ctx["stats"], "sources": ctx["ok_sources"]}
    index["days"] = [d for d in index["days"] if d.get("date") != date]
    index["days"].append(entry)
    index["days"].sort(key=lambda d: d["date"], reverse=True)
    index["days"] = index["days"][:365]
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)

    # 站点根目录下给 GitHub Pages 之外的静态消费方留一份 latest.json
    with open(os.path.join(DATA_DIR, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(ctx["raw"], f, ensure_ascii=False, indent=1)
