# last30days 快速上手指南

**零配置研究工具** — 无需任何 API Key，即刻开始使用。

## 功能简介

last30days 是一个深度研究引擎，可以从多个技术社区聚合最近 30 天的热门内容：
- **Hacker News** — YC 技术社区热门
- **Reddit** — 英文社区讨论
- **V2EX** — 中文技术社区（本 PR 新增）
- **HuggingFace** — AI 模型趋势（本 PR 新增）

## 快速开始

### 基础用法

```bash
# 聚合所有来源（默认每个来源 10 条）
python3 scripts/last30days_lite.py

# 搜索特定主题
python3 scripts/last30days_lite.py --topic "AI coding"

# 只获取特定来源
python3 scripts/last30days_lite.py --sources hn,v2ex,hf

# 调整条数
python3 scripts/last30days_lite.py --limit 20

# JSON 输出（便于程序处理）
python3 scripts/last30days_lite.py --output json

# 保存到文件
python3 scripts/last30days_lite.py --save
```

### 数据来源

| 来源 | 描述 | 需要 API Key |
|------|------|-------------|
| Hacker News (`hn`) | 美国技术社区热门 | ❌ 不需要 |
| Reddit (`reddit`) | 英文社区讨论 | ❌ 不需要（RSS） |
| V2EX (`v2ex`) | 中文技术社区 | ❌ 不需要 |
| HuggingFace (`hf`) | AI 模型趋势 | ❌ 不需要 |

### 输出示例

```
# 📊 最近30天热门 - 2026-04-03

总计: 40 条

## Hacker News (10 条)
----------------------------------------
1. [Claude Code's source code has been leaked...]
   ⭐ 2069 | 💬 1017

## V2EX (10 条)
----------------------------------------
1. [尴尬了，可能招聘了一个不会手写代码的 AI 工程师]
   📍 career | 💬 100 | 🔥 hot

2. [国产大模型对比：DeepSeek vs Qwen vs GLM]
   📍 ai | 💬 85 | 🆕 latest

## HuggingFace (10 条)
----------------------------------------
1. [meta-llama/Llama-4-Maverick-17B-128E-Instruct]
   📥 1.2M | ❤️ 3.5K | ⭐ excellent

2. [deepseek-ai/DeepSeek-V3-Base]
   📥 890K | ❤️ 2.1K | 👍 good

## Reddit (10 条)
----------------------------------------
1. [Announcement: Temporary LLM Content Ban]
   📍 r/programming
```

## 质量评分

HuggingFace 模型会根据「点赞/下载比」显示质量标签：

| 标签 | 含义 | 点赞/下载比 |
|------|------|-----------|
| ⭐ excellent | 优秀 | ≥ 5% |
| 👍 good | 良好 | ≥ 2% |
| ✓ acceptable | 可接受 | ≥ 0.5% |

这个比率反映了社区对模型的认可度。一个下载量高但点赞少的模型可能是「被广泛使用但口碑一般」。

## V2EX 双端点

V2EX 支持两个数据端点：

1. **Hot（热门）** — 高热度话题，回复数多
2. **Latest（最新）** — 新发布话题，发现新兴讨论

默认会同时获取两个端点，去重后返回。

## 使用场景

### 1. 催化剂研究（投资相关）

```bash
# 研究某个技术趋势
python3 scripts/last30days_lite.py --topic "AI video generation" --sources hn,v2ex,hf

# 输出可用于 Investment Commander 的催化剂分析
```

### 2. 行业热度分析

```bash
# 查看某个行业在技术社区的讨论热度
python3 scripts/last30days_lite.py --topic "quantum computing" --save
```

### 3. AI 模型选型

```bash
# 对比同类模型的社区认可度
python3 scripts/last30days_lite.py --topic "llama" --sources hf --output json
```

## 与 Investment Commander 集成

last30days 已集成到 Investment Commander 作为基础设施层：

```
用户: 研究 AI 视频生成工具的热度

Commander:
  → 调用 last30days_lite.py --topic "AI video generation"
  → 聚合 HN + V2EX + HuggingFace + Reddit
  → 格式化为投资启示
```

## 输出目录

```bash
skills/last30days/
├── output/
│   └── YYYY-MM-DD-trends.md    # 保存的报告
├── scripts/
│   ├── last30days_lite.py      # 免费版入口
│   └── lib/
│       ├── v2ex.py             # V2EX 模块
│       └── huggingface.py      # HuggingFace 模块
└── docs/
    ├── free-mode.md            # 英文文档
    └── quickstart-zh.md        # 本文档
```

## 常见问题

### Q: 为什么有些模型下载量很高但没有质量标签？

A: 点赞/下载比低于 0.5% 的模型不会显示质量标签。这可能意味着该模型被广泛下载但社区评价一般。

### Q: V2EX 的 hot 和 latest 有什么区别？

A: Hot 是当前热门话题（回复数多），Latest 是最新发布的话题。Latest 可以帮你发现还没火起来的新兴讨论。

### Q: 可以只用中文社区的数据吗？

A: 可以，使用 `--sources v2ex` 只获取 V2EX 数据。

---

**问题反馈**：https://github.com/mvanhorn/last30days-skill/issues

**PR 贡献者**：Alan Li (https://github.com/Alan5168)