#!/usr/bin/env python
"""入口：抓取全部信息源 → 生成当天的 Jekyll 日报 → 写归档。

每个源独立失败降级，单个源挂掉不会让整期日报缺失。
"""
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402
from fetcher import FetchError  # noqa: E402
import render  # noqa: E402
import summarize  # noqa: E402
from sources import (alphaxiv, arxiv_csai, artificial_analysis,  # noqa: E402
                     hf_papers, smolai, the_batch)

SOURCES = [
    ("smolai", smolai.fetch),
    ("the_batch", the_batch.fetch),
    ("hf_papers", hf_papers.fetch),
    ("arxiv", arxiv_csai.fetch),
    ("artificial_analysis", artificial_analysis.fetch),
    ("alphaxiv", alphaxiv.fetch),
]

SNAPSHOT = os.path.join(config.DATA_DIR, "aa_snapshot.json")


def count_of(key: str, block: dict) -> int:
    if not block:
        return 0
    if key == "smolai":
        return len(block.get("issues", []))
    if key == "the_batch":
        return len(block.get("articles", []))
    if key in ("hf_papers", "arxiv"):
        return len(block.get("papers", []))
    if key == "artificial_analysis":
        return len(block.get("models", []))
    if key == "alphaxiv":
        return len(block.get("items", []))
    return 0


def models_diff(block: dict) -> dict:
    """和上一次快照对比，找出新上榜模型与分数变化。"""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    try:
        with open(SNAPSHOT, "r", encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = {}

    models = (block or {}).get("all") or []
    if not models:
        return {}

    new_map = {m["family"]: m["intelligence"] for m in models}
    is_first = not old.get("models")

    new_entries = [
        {"family": m["family"], "creator": m["creator"], "intelligence": m["intelligence"]}
        for m in models if m["family"] not in (old.get("models") or {})
    ] if not is_first else []

    moved = []
    if not is_first:
        for fam, val in new_map.items():
            prev = (old.get("models") or {}).get(fam)
            if prev is None:
                continue
            delta = round(val - prev, 1)
            if abs(delta) >= 1:
                moved.append({"family": fam, "old": prev, "new": val, "delta": delta})
        moved.sort(key=lambda x: -abs(x["delta"]))

    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump({"date": config.today().strftime("%Y-%m-%d"), "models": new_map}, f,
                  ensure_ascii=False, indent=1)

    return {"new": new_entries, "moved": moved, "is_first": is_first}


def dedupe_papers(blocks: dict) -> int:
    """HuggingFace 热门论文和 arXiv 会同时出现同一篇，arXiv 侧剔除重复项。"""
    hf_ids = {p.get("id") for p in (blocks.get("hf_papers") or {}).get("papers", []) if p.get("id")}
    arxiv = (blocks.get("arxiv") or {}).get("papers")
    if not hf_ids or not arxiv:
        return 0
    kept = [p for p in arxiv if p.get("id") not in hf_ids]
    removed = len(arxiv) - len(kept)
    blocks["arxiv"]["papers"] = kept
    return removed


def maybe_summarize(blocks: dict) -> None:
    """LLM 模式开启时，为论文补一句中文摘要。"""
    if not summarize.enabled():
        return
    for key in ("hf_papers", "arxiv"):
        for p in (blocks.get(key) or {}).get("papers", []):
            zh = summarize.summarize_one(p.get("title", ""), p.get("summary", ""))
            if zh:
                p["zh"] = zh


def main() -> int:
    today = config.today()
    date_str = today.strftime("%Y-%m-%d")
    print(f"[ai-daily] 生成日期：{date_str}")

    blocks, failed, ok_sources, source_rows = {}, [], [], []
    for key, fn in SOURCES:
        t0 = time.time()
        try:
            block = fn(today)
            blocks[key] = block
            ok_sources.append(block.get("name", key))
            status = "🔗 链接模式" if block.get("mode") == "link" else "✅"
            source_rows.append({"name": block.get("name", key), "status": status,
                                "count": count_of(key, block)})
            print(f"  ✓ {key:<20} {count_of(key, block):>3} 条  ({time.time() - t0:.1f}s)")
        except Exception as e:
            failed.append(key)
            source_rows.append({"name": key, "status": "❌", "count": 0})
            print(f"  ✗ {key:<20} 失败：{e}")
            if os.environ.get("DEBUG"):
                traceback.print_exc()

    removed = dedupe_papers(blocks)
    if removed:
        print(f"  · arXiv 与 HuggingFace 重复，已去重 {removed} 篇")
    maybe_summarize(blocks)

    n_papers = count_of("hf_papers", blocks.get("hf_papers")) + count_of("arxiv", blocks.get("arxiv"))
    n_news = count_of("smolai", blocks.get("smolai")) + count_of("the_batch", blocks.get("the_batch"))
    stats = f"{n_news} 条要闻 · {n_papers} 篇论文 · {count_of('artificial_analysis', blocks.get('artificial_analysis'))} 个模型"

    ctx = {
        "date": date_str,
        "blocks": blocks,
        "ok_sources": ok_sources,
        "failed": failed,
        "source_rows": source_rows,
        "stats": stats,
        "models_diff": models_diff(blocks.get("artificial_analysis")),
        "raw": {"date": date_str, "stats": stats, "sources": blocks},
    }

    post_path, data_path = render.write_outputs(ctx)
    rel_post = os.path.relpath(post_path, config.ROOT)
    print(f"[ai-daily] 已写入 {rel_post}")
    print(f"[ai-daily] 已写入 data/{os.path.basename(data_path)}")
    print(f"[ai-daily] 汇总：{stats}")

    if len(ok_sources) == 0:
        print("[ai-daily] 所有源均失败，不提交本次结果", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
