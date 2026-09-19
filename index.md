---
layout: default
title: 首页
---

<p class="note">每天自动抓取 6 个 AI 信息源，汇总成一篇文章。最近 20 期：</p>

<ul class="archive-list">
{% for post in site.posts limit:20 %}
  <li>
    <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
    <span class="meta-line">{{ post.date | date: "%Y-%m-%d" }}{% if post.stats_summary %} · {{ post.stats_summary }}{% endif %}</span>
  </li>
{% endfor %}
</ul>

<h2>信息源</h2>
<ul>
  <li><a href="https://news.smol.ai/">AINews (smol.ai)</a> — 工作日 AI 工程要闻速览</li>
  <li><a href="https://www.deeplearning.ai/the-batch">The Batch</a> — DeepLearning.AI 周报</li>
  <li><a href="https://huggingface.co/papers">Hugging Face Daily Papers</a> — 社区热度论文</li>
  <li><a href="https://arxiv.org/list/cs.AI/recent">arXiv cs.AI</a> — 最新人工智能预印本</li>
  <li><a href="https://artificialanalysis.ai/">Artificial Analysis</a> — 模型智能指数 / 价格 / 速度榜单</li>
  <li><a href="https://www.alphaxiv.org/">alphaXiv</a> — 论文阅读与解读（以直达链接形式附在每篇论文后）</li>
</ul>
