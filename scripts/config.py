"""全局配置。所有阈值都可用环境变量覆盖，方便在 GitHub Actions 里调。"""
import os
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))  # Asia/Shanghai


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "")
    if v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def today() -> datetime:
    """今天（上海时区）。可用 DAILY_DATE=YYYY-MM-DD 覆盖，便于补跑历史日期。"""
    forced = os.environ.get("DAILY_DATE", "").strip()
    if forced:
        try:
            return datetime.strptime(forced, "%Y-%m-%d").replace(tzinfo=TZ)
        except ValueError:
            pass
    return datetime.now(TZ)


# ── 抓取规模 ───────────────────────────────────────────────
TOP_PAPERS = _int("TOP_PAPERS", 12)        # HuggingFace 每日论文
TOP_ARXIV = _int("TOP_ARXIV", 15)          # arXiv cs.AI 最新条目
TOP_MODELS = _int("TOP_MODELS", 12)        # Artificial Analysis 榜单
SMOL_ITEMS = _int("SMOL_ITEMS", 3)         # smol.ai 取最近几期
BATCH_ARTICLES = _int("BATCH_ARTICLES", 8)  # The Batch 单期最多取几篇
LOOKBACK_DAYS = _int("LOOKBACK_DAYS", 3)   # 各源允许的时间回退窗口（天）

# ── 开关 ───────────────────────────────────────────────────
# alphaXiv 是纯前端渲染站点，默认不做浏览器抓取；改为给每篇论文附加直达链接。
# 想启用浏览器抓取：设置 ALPHAXIV_BROWSER=1 并在 Actions 里装 playwright。
ALPHAXIV_BROWSER = _bool("ALPHAXIV_BROWSER", False)

# 摘要模式：rule（默认，规则提取）/ llm（需配置 LLM_API_KEY + LLM_BASE_URL + LLM_MODEL）
SUMMARY_MODE = os.environ.get("SUMMARY_MODE", "rule").strip().lower()
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

TIMEOUT = _int("TIMEOUT", 30)

# 站点根目录（脚本所在目录的上一级）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "_posts")
DATA_DIR = os.path.join(ROOT, "data")
