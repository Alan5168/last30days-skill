# Free Mode: Zero-API Sources

last30days now supports additional **free sources** that require no API keys, expanding coverage to Chinese tech community (V2EX) and AI models (HuggingFace).

## New Free Sources

| Source | Description | API Required |
|--------|-------------|--------------|
| **V2EX** | Chinese tech community hot topics | ❌ None |
| **HuggingFace** | Trending AI models (downloads, likes) | ❌ None |
| **Hacker News** | Already supported via Algolia | ❌ None |
| **Reddit RSS** | Fallback when no ScrapeCreators key | ❌ None |

## Using Free Mode

```bash
# Run free mode aggregation
python3 scripts/last30days_lite.py

# Search specific topic
python3 scripts/last30days_lite.py --topic "AI coding"

# Specific sources only
python3 scripts/last30days_lite.py --sources hn,v2ex,hf

# JSON output
python3 scripts/last30days_lite.py --output json --save
```

## V2EX Integration

V2EX is a popular Chinese tech community (similar to Hacker News). The free mode fetches hot topics from:

- `https://www.v2ex.com/api/topics/hot.json`
- Returns: title, node (category), replies, author, URL

Example output:
```
## V2EX (10 条)
----------------------------------------
1. [尴尬了，可能招聘了一个不会手写代码的 AI 工程师]
   📍 career | 💬 100
```

## HuggingFace Integration

Tracks trending AI models from HuggingFace Hub:

- `https://huggingface.co/api/models`
- Sorted by downloads
- Returns: modelId, downloads, likes, tags, URL

Example output:
```
## HuggingFace (10 条)
----------------------------------------
1. [meta-llama/Llama-4-Maverick-17B-128E-Instruct]
   📥 1.2M | ❤️ 3.5K
```

## Comparison: Free vs Full Mode

| Feature | Free Mode | Full Mode |
|---------|-----------|-----------|
| Hacker News | ✅ Algolia | ✅ Algolia |
| Reddit | ✅ RSS (limited) | ✅ ScrapeCreators (comments) |
| V2EX | ✅ | ❌ |
| HuggingFace | ✅ | ❌ |
| X/Twitter | ❌ | ✅ (cookies/xAI) |
| YouTube | ❌ | ✅ (yt-dlp) |
| TikTok | ❌ | ✅ (ScrapeCreators) |
| Instagram | ❌ | ✅ (ScrapeCreators) |
| Polymarket | ❌ | ✅ |
| Bluesky | ❌ | ✅ |

## When to Use Free Mode

- **No API keys configured** - Get started immediately
- **Chinese tech topics** - V2EX coverage not in full mode
- **AI model research** - HuggingFace trending models
- **Quick aggregation** - Faster than full 10-source scan

## Contribution

This free mode module was contributed by [Alan Li](https://github.com/Alan5168) via `last30days_lite.py`.

---

*Expanding last30days coverage to global tech communities — no API keys required.*