"""V2EX topics fetcher - Chinese tech community.

Uses V2EX public API to fetch hot and latest topics from v2ex.com.
No API key required.
"""

import sys
import time
from typing import Any, Dict, List, Optional

from . import http

V2EX_HOT_URL = "https://www.v2ex.com/api/topics/hot.json"
V2EX_LATEST_URL = "https://www.v2ex.com/api/topics/latest.json"

DEPTH_CONFIG = {
    "quick": 10,
    "default": 20,
    "deep": 30,
}

# How many latest topics to fetch relative to depth
LATEST_MULTIPLIER = 3  # Fetch 3x more latest topics for broader coverage


def _log(msg: str):
    """Log to stderr (only in TTY mode to avoid cluttering Claude Code output)."""
    if sys.stderr.isatty():
        sys.stderr.write(f"[V2EX] {msg}\n")
        sys.stderr.flush()


def fetch_v2ex_hot(
    topic: Optional[str] = None,
    depth: str = "default",
) -> List[Dict[str, Any]]:
    """Fetch hot topics from V2EX.

    Args:
        topic: Optional topic filter (case-insensitive substring match)
        depth: 'quick', 'default', or 'deep'

    Returns:
        List of topic dicts with title, url, node, author, replies.
    """
    count = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])
    _log(f"Fetching {count} hot topics" + (f" (filter: {topic})" if topic else ""))

    try:
        response = http.request("GET", V2EX_HOT_URL, timeout=15)
    except Exception as e:
        _log(f"Fetch failed: {e}")
        return []

    topics = response if isinstance(response, list) else []
    
    items = []
    for t in topics[:count]:
        title = t.get("title", "")
        
        # Topic filter (case-insensitive)
        if topic and topic.lower() not in title.lower():
            continue
        
        items.append({
            "id": t.get("id"),
            "title": title,
            "url": t.get("url", ""),
            "node": t.get("node", {}).get("name", ""),
            "node_title": t.get("node", {}).get("title", ""),
            "author": t.get("member", {}).get("username", ""),
            "replies": t.get("replies", 0),
            "created": t.get("created", 0),
            "source": "v2ex",
            "type": "hot",
        })

    _log(f"Found {len(items)} hot topics")
    return items


def fetch_v2ex_latest(
    topic: Optional[str] = None,
    depth: str = "default",
) -> List[Dict[str, Any]]:
    """Fetch latest topics from V2EX.

    Provides broader coverage beyond just "hot" topics.
    Useful for discovering emerging discussions.

    Args:
        topic: Optional topic filter (case-insensitive substring match)
        depth: 'quick', 'default', or 'deep'

    Returns:
        List of topic dicts with title, url, node, author, replies.
    """
    base_count = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])
    count = base_count * LATEST_MULTIPLIER  # Fetch more for broader coverage
    _log(f"Fetching {count} latest topics" + (f" (filter: {topic})" if topic else ""))

    try:
        response = http.request("GET", V2EX_LATEST_URL, timeout=15)
    except Exception as e:
        _log(f"Fetch failed: {e}")
        return []

    topics = response if isinstance(response, list) else []
    
    items = []
    for t in topics[:count]:
        title = t.get("title", "")
        
        # Topic filter (case-insensitive)
        if topic and topic.lower() not in title.lower():
            continue
        
        items.append({
            "id": t.get("id"),
            "title": title,
            "url": t.get("url", ""),
            "node": t.get("node", {}).get("name", ""),
            "node_title": t.get("node", {}).get("title", ""),
            "author": t.get("member", {}).get("username", ""),
            "replies": t.get("replies", 0),
            "created": t.get("created", 0),
            "source": "v2ex",
            "type": "latest",
        })

    _log(f"Found {len(items)} latest topics")
    return items


def fetch_v2ex(
    topic: Optional[str] = None,
    depth: str = "default",
    include_latest: bool = True,
) -> List[Dict[str, Any]]:
    """Fetch both hot and latest topics from V2EX.

    Combines hot (trending) and latest (emerging) for comprehensive coverage.
    Deduplicates by topic ID.

    Args:
        topic: Optional topic filter (case-insensitive substring match)
        depth: 'quick', 'default', or 'deep'
        include_latest: Whether to include latest topics (default: True)

    Returns:
        List of topic dicts with title, url, node, author, replies.
    """
    all_items = []
    seen_ids = set()
    
    # Fetch hot topics first (higher priority)
    hot_items = fetch_v2ex_hot(topic=topic, depth=depth)
    for item in hot_items:
        if item["id"] not in seen_ids:
            seen_ids.add(item["id"])
            all_items.append(item)
    
    # Fetch latest topics for broader coverage
    if include_latest:
        latest_items = fetch_v2ex_latest(topic=topic, depth=depth)
        for item in latest_items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                all_items.append(item)
    
    _log(f"Total unique topics: {len(all_items)}")
    return all_items


def parse_v2ex_response(items: List[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
    """Parse V2EX items into normalized format.

    Args:
        items: Raw V2EX topic list
        query: Original search query for relevance scoring

    Returns:
        List of normalized item dicts.
    """
    from .relevance import token_overlap_relevance
    
    normalized = []
    for i, item in enumerate(items):
        # Simple relevance scoring
        # Hot topics get a boost
        type_boost = 0.1 if item.get("type") == "hot" else 0.0
        rank_score = max(0.3, 1.0 - (i * 0.02)) + type_boost
        engagement_boost = min(0.15, item.get("replies", 0) / 100)
        
        if query:
            content_score = token_overlap_relevance(query, item.get("title", ""))
            relevance = min(1.0, 0.5 * rank_score + 0.35 * content_score + engagement_boost)
        else:
            relevance = min(1.0, rank_score * 0.7 + engagement_boost + 0.15)

        normalized.append({
            "object_id": str(item.get("id", "")),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "author": item.get("author", ""),
            "date": None,  # V2EX doesn't provide date in hot API
            "engagement": {
                "replies": item.get("replies", 0),
                "node": item.get("node_title", item.get("node", "")),
                "type": item.get("type", "unknown"),
            },
            "relevance": round(relevance, 2),
            "why_relevant": f"V2EX {item.get('type', 'hot')} topic in {item.get('node_title', item.get('node', 'unknown'))}",
            "source": "v2ex",
        })

    return normalized