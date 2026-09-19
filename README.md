# AI 日报 · 自动聚合博客

每天自动抓取 6 个 AI 信息源，生成一篇中文框架 + 原文链接的日报，推送到 GitHub Pages 博客。
**零依赖**（只用 Python 标准库）、**零服务器**（全部跑在 GitHub Actions 上）。

## 信息源与抓取方式

| 信息源 | 抓取方式 | 说明 |
|---|---|---|
| [AINews (smol.ai)](https://news.smol.ai/) | RSS 全文 | 工作日 AI 工程要闻，RSS 带完整正文 |
| [The Batch](https://www.deeplearning.ai/the-batch) | 页面解析 | 站点无 RSS；解析最新一期 issue 页的 `h1` 列表，标题即锚点 id，可拼出独立文章链接 |
| [Hugging Face Daily Papers](https://huggingface.co/papers) | 官方 API | `/api/daily_papers`，按热度排序 |
| [arXiv cs.AI](https://arxiv.org/list/cs.AI/recent) | 官方 API | 按提交时间倒序取最新 40 条。**没用 RSS**：RSS 周末返回空 channel，会让日报缺一大块 |
| [Artificial Analysis](https://artificialanalysis.ai/) | RSC 数据解析 | 官方 API 要 key（401），改为解析榜单页的 React Flight 数据，能拿到 190+ 模型族 |
| [alphaXiv](https://www.alphaxiv.org/) | 链接增强 | 纯前端渲染，服务端拿不到数据，不硬抓；改为给每篇论文附 `alphaxiv.org/abs/<id>` 直达链接 |

> 站点改版会让某个源的解析失效。每个源都独立失败降级：挂掉的源在日报末尾标红，其余源照常出内容，不会整期跑空。

## 部署到你的 GitHub

### 1. 建仓库并推送

```bash
cd ai-daily
git init
git add .
git commit -m "init: AI 日报聚合博客"

# 在 GitHub 上新建一个空仓库，比如叫 ai-daily，然后：
git remote add origin git@github.com:<你的用户名>/ai-daily.git
git branch -M main
git push -u origin main
```

### 2. 开启 GitHub Pages

仓库 **Settings → Pages → Build and deployment**：
- Source 选 **Deploy from a branch**
- Branch 选 **main**，目录选 **/ (root)**
- 保存，等一两分钟，访问 `https://<你的用户名>.github.io/ai-daily/`

### 3. 仓库名不是 `ai-daily` 时

改 `_config.yml` 里的两行：

```yaml
baseurl: "/你的仓库名"   # 仓库名 ≠ ai-daily 时改这里；用 <用户名>.github.io 仓库则留空字符串
url: "https://<你的用户名>.github.io"
```

### 4. 确认定时任务的权限

仓库 **Settings → Actions → General → Workflow permissions**，勾选
**Read and write permissions**。之后每天北京时间 13:00 会自动跑一次。

想立刻看效果：仓库 **Actions → Daily AI Digest → Run workflow**，可以不填日期直接跑。

## 本地运行

```bash
python scripts/main.py              # 抓取并生成 _posts/YYYY-MM-DD-ai-daily.md
DAILY_DATE=2026-09-18 python scripts/main.py   # 补跑指定日期
DEBUG=1 python scripts/main.py      # 打印失败源的详细堆栈
```

产物：

```
_posts/2026-09-19-ai-daily.md    # 当天日报（Jekyll 文章）
data/2026-09-19.json             # 当天结构化数据
data/index.json                  # 归档索引（最多 365 天）
data/aa_snapshot.json            # 榜单快照，用于和新模型/分数变化对比
```

## 可调参数

在 Actions 的 `env:` 里改，或本地用环境变量：

| 变量 | 默认 | 含义 |
|---|---|---|
| `TOP_PAPERS` | 12 | HuggingFace 论文条数 |
| `TOP_ARXIV` | 15 | arXiv 条数 |
| `TOP_MODELS` | 12 | 榜单模型数 |
| `SMOL_ITEMS` | 3 | AINews 取几期 |
| `BATCH_ARTICLES` | 8 | The Batch 单期取几篇 |
| `LOOKBACK_DAYS` | 3 | 时间回看窗口（天） |
| `DAILY_DATE` | 今天 | 补跑指定日期 |

## 让摘要真正变成中文（可选）

默认是 **规则提取**：直接用源站的标题和摘要原文（信息不失真、零成本），
日报的框架、栏目、指标说明都是中文。

想要「每篇一句中文摘要」，切到 LLM 模式：

1. 仓库 **Settings → Secrets and variables → Actions → New repository secret**，加 `LLM_API_KEY`
2. 编辑 `.github/workflows/daily.yml`，取消注释这三行：

```yaml
          SUMMARY_MODE: llm
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_MODEL: deepseek-chat      # 或 gpt-4o-mini 等
```

用的是 OpenAI 兼容接口，DeepSeek / OpenAI / Moonshot / 通义都行，改 `LLM_BASE_URL` 即可。
摘要结果缓存在 `data/summary_cache.json`，同一篇论文不会重复计费。

## alphaXiv 浏览器模式（可选）

默认不抓（站点纯前端渲染）。如果你一定要它的首页趋势列表：

```bash
pip install playwright && playwright install chromium
export ALPHAXIV_BROWSER=1
python scripts/main.py
```

在 Actions 里用会明显变慢（要装 Chromium），一般不建议。

## 目录结构

```
ai-daily/
├── _config.yml            Jekyll 配置（改名记得改 baseurl）
├── _layouts/              页面模板
├── _posts/                每天生成的日报
├── assets/css/style.css   样式
├── data/                  结构化归档 + 榜单快照
├── index.md               首页（列出最近 20 期）
├── scripts/
│   ├── main.py            入口：抓取 → 渲染 → 写盘
│   ├── config.py          全部可调参数
│   ├── fetcher.py         统一 HTTP（UA / 超时 / 重试 / gzip）
│   ├── rss.py             RSS + Atom 解析
│   ├── render.py          Markdown 渲染
│   ├── summarize.py       规则 / LLM 两种摘要模式
│   └── sources/           每个源一个文件
└── .github/workflows/daily.yml
```
