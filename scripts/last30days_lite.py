#!/usr/bin/env python3
"""
last30days-lite - 免费版30天热门聚合

从 Hacker News、Reddit、V2EX、HuggingFace 聚合最近30天热门内容。
无需任何 API Key。

使用方法:
  python3 last30days_lite.py
  python3 last30days_lite.py --topic "AI coding"
  python3 last30days_lite.py --sources hn,v2ex --limit 20
  python3 last30days_lite.py --output json --save
"""

import argparse
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import feedparser
import time
import re

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 默认 Reddit 子版块
DEFAULT_SUBREDDITS = ["programming", "MachineLearning", "artificial"]


def fetch_hacker_news(limit=30, topic=None):
    """Hacker News 最近30天热门帖子（Algolia API）"""
    url = "https://hn.algolia.com/api/v1/search"
    
    # 最近30天的 Unix 时间戳
    days_30 = int((datetime.now() - timedelta(days=30)).timestamp())
    
    params = {
        "tags": "story",
        "hitsPerPage": limit,
        "numericFilters": f"created_at_i>{days_30}"
    }
    
    # 如果有主题，添加搜索词
    if topic:
        params["query"] = topic
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        items = []
        for hit in data.get("hits", []):
            items.append({
                "source": "Hacker News",
                "title": hit.get("title", ""),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "points": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
                "author": hit.get("author", ""),
                "time": hit.get("created_at", ""),
                "id": hit.get("objectID", "")
            })
        return items
    except Exception as e:
        print(f"❌ Hacker News fetch error: {e}")
        return []


def fetch_reddit(subreddits=None, limit=30, topic=None):
    """Reddit 热门帖子（RSS，无需 API Key）"""
    if subreddits is None:
        subreddits = DEFAULT_SUBREDDITS
    
    all_items = []
    
    for subreddit in subreddits:
        url = f"https://www.reddit.com/r/{subreddit}/hot/.rss"
        
        try:
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:limit // len(subreddits)]:
                title = entry.get("title", "")
                
                # 如果有主题，简单过滤
                if topic and topic.lower() not in title.lower():
                    continue
                
                all_items.append({
                    "source": "Reddit",
                    "subreddit": subreddit,
                    "title": title,
                    "url": entry.get("link", ""),
                    "author": entry.get("author", ""),
                    "time": entry.get("published", ""),
                    "summary": entry.get("summary", "")[:200] if entry.get("summary") else ""
                })
            
            time.sleep(0.3)  # 避免请求过快
        except Exception as e:
            print(f"❌ Reddit r/{subreddit} fetch error: {e}")
    
    return all_items[:limit]


def fetch_v2ex(limit=30, topic=None):
    """V2EX 热门话题"""
    url = "https://www.v2ex.com/api/topics/hot.json"
    
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        
        items = []
        for topic_item in data[:limit]:
            title = topic_item.get("title", "")
            
            # 如果有主题，简单过滤
            if topic and topic.lower() not in title.lower():
                continue
            
            items.append({
                "source": "V2EX",
                "title": title,
                "url": topic_item.get("url", ""),
                "node": topic_item.get("node", {}).get("name", ""),
                "author": topic_item.get("member", {}).get("username", ""),
                "replies": topic_item.get("replies", 0),
                "time": topic_item.get("created", "")
            })
        return items
    except Exception as e:
        print(f"❌ V2EX fetch error: {e}")
        return []


def fetch_huggingface(limit=30, topic=None):
    """HuggingFace 最近热门模型"""
    url = "https://huggingface.co/api/models"
    
    # 最近30天
    days_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    params = {
        "sort": "downloads",
        "direction": -1,
        "limit": limit * 2  # 多取一些，后面过滤
    }
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        
        items = []
        for model in data:
            model_id = model.get("modelId", "")
            
            # 如果有主题，简单过滤
            if topic and topic.lower() not in model_id.lower():
                continue
            
            items.append({
                "source": "HuggingFace",
                "title": model_id,
                "url": f"https://huggingface.co/{model_id}",
                "downloads": model.get("downloads", 0),
                "likes": model.get("likes", 0),
                "tags": model.get("tags", []),
                "time": model.get("createdAt", "")
            })
            
            if len(items) >= limit:
                break
        
        return items
    except Exception as e:
        print(f"❌ HuggingFace fetch error: {e}")
        return []


def aggregate_all(sources=None, limit=30, topic=None):
    """聚合所有来源"""
    all_sources = {
        "hn": ("Hacker News", fetch_hacker_news),
        "reddit": ("Reddit", lambda l, t: fetch_reddit(limit=l, topic=t)),
        "v2ex": ("V2EX", fetch_v2ex),
        "hf": ("HuggingFace", fetch_huggingface)
    }
    
    if sources:
        source_keys = sources.split(",")
    else:
        source_keys = list(all_sources.keys())
    
    results = []
    for key in source_keys:
        if key in all_sources:
            name, fetch_fn = all_sources[key]
            print(f"🔄 Fetching {name}...")
            items = fetch_fn(limit, topic)
            results.extend(items)
            time.sleep(0.5)  # 避免请求过快
    
    return results


def format_report(items, output_format="text", topic=None):
    """格式化输出"""
    if output_format == "json":
        return json.dumps(items, indent=2, ensure_ascii=False)
    
    # Text format
    title = f"最近30天热门 - {datetime.now().strftime('%Y-%m-%d')}"
    if topic:
        title = f"最近30天热门: {topic} - {datetime.now().strftime('%Y-%m-%d')}"
    
    lines = [f"# 📊 {title}", f"\n总计: {len(items)} 条\n"]
    
    # 按来源分组
    by_source = {}
    for item in items:
        src = item.get("source", "Unknown")
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(item)
    
    for src, src_items in by_source.items():
        lines.append(f"\n## {src} ({len(src_items)} 条)")
        lines.append("-" * 50)
        
        for i, item in enumerate(src_items[:15], 1):
            title_text = item.get("title", "")
            url = item.get("url", "")
            extra = ""
            
            if src == "Hacker News":
                extra = f"⭐ {item.get('points', 0)} | 💬 {item.get('comments', 0)}"
            elif src == "V2EX":
                extra = f"📍 {item.get('node', '')} | 💬 {item.get('replies', 0)}"
            elif src == "HuggingFace":
                downloads = item.get('downloads', 0)
                if downloads >= 1_000_000:
                    dl_str = f"{downloads/1_000_000:.1f}M"
                elif downloads >= 1_000:
                    dl_str = f"{downloads/1_000:.1f}K"
                else:
                    dl_str = str(downloads)
                extra = f"📥 {dl_str} | ❤️ {item.get('likes', 0)}"
            elif src == "Reddit":
                extra = f"📍 r/{item.get('subreddit', '')}"
            
            # 截断标题
            display_title = title_text[:60] + "..." if len(title_text) > 60 else title_text
            lines.append(f"{i}. [{display_title}]({url})")
            if extra:
                lines.append(f"   {extra}")
    
    # 添加统计
    lines.append("\n---")
    lines.append(f"\n📚 来源: {', '.join(by_source.keys())}")
    lines.append(f"⏰ 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="last30days-lite - 免费30天热门聚合",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 last30days_lite.py
  python3 last30days_lite.py --topic "AI coding"
  python3 last30days_lite.py --sources hn,v2ex --limit 20
  python3 last30days_lite.py --output json --save
        """
    )
    parser.add_argument("--topic", help="搜索主题（可选）")
    parser.add_argument("--sources", help="指定来源，逗号分隔 (hn,reddit,v2ex,hf)")
    parser.add_argument("--limit", type=int, default=30, help="每个来源条数（默认30）")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--save", action="store_true", help="保存到文件")
    
    args = parser.parse_args()
    
    items = aggregate_all(args.sources, args.limit, args.topic)
    report = format_report(items, args.output, args.topic)
    
    print(report)
    
    if args.save:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}-last30days"
        if args.topic:
            # 清理文件名
            safe_topic = re.sub(r'[^\w\s-]', '', args.topic).strip().replace(' ', '-')
            filename += f"-{safe_topic}"
        filename += ".md"
        
        out_file = OUTPUT_DIR / filename
        out_file.write_text(report)
        print(f"\n✅ 已保存到 {out_file}")
    
    return items


if __name__ == "__main__":
    main()