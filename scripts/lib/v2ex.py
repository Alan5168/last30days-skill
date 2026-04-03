"""V2EX hot topics fetcher - Chinese tech community.

Uses V2EX public API to fetch hot topics from v2ex.com.
No API key required.
"""

import sys
import time
from typing import Any, Dict, List, Optional

from . import http

V2EX_HOT_URL = "https://www.v2ex.com/api/topics/hot.json"

DEPTH_CONFIG = {
    "quick": 10,
    "default": 20,
    "deep": 30,
}


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
        })

    _log(f"Found {len(items)} topics")
    return items


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
        rank_score = max(0.3, 1.0 - (i * 0.03))
        engagement_boost = min(0.15, item.get("replies", 0) / 100)
        if query:
            content_score = token_overlap_relevance(query, item.get("title", ""))
            relevance = min(1.0, 0.5 * rank_score + 0.4 * content_score + engagement_boost)
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
            },
            "relevance": round(relevance, 2),
            "why_relevant": f"V2EX hot topic in {item.get('node_title', item.get('node', 'unknown'))}",
            "source": "v2ex",
        })

    return normalized