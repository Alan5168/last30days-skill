"""HuggingFace models fetcher - Popular AI models from huggingface.co.

Uses HuggingFace public API to fetch trending models.
No API key required.
"""

import math
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from . import http

HF_MODELS_URL = "https://huggingface.co/api/models"

DEPTH_CONFIG = {
    "quick": 15,
    "default": 30,
    "deep": 50,
}


def _log(msg: str):
    """Log to stderr (only in TTY mode to avoid cluttering Claude Code output)."""
    if sys.stderr.isatty():
        sys.stderr.write(f"[HuggingFace] {msg}\n")
        sys.stderr.flush()


def fetch_huggingface_models(
    topic: Optional[str] = None,
    depth: str = "default",
    days: int = 30,
) -> List[Dict[str, Any]]:
    """Fetch popular models from HuggingFace.

    Args:
        topic: Optional topic filter (case-insensitive substring match on model ID)
        depth: 'quick', 'default', or 'deep'
        days: Only include models from last N days (0 = no filter)

    Returns:
        List of model dicts with modelId, downloads, likes, tags.
    """
    count = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])
    _log(f"Fetching {count} models" + (f" (filter: {topic})" if topic else ""))

    params = {
        "sort": "downloads",
        "direction": -1,
        "limit": count * 2,  # Fetch more to filter later
    }

    try:
        response = http.request("GET", HF_MODELS_URL, params=params, timeout=30)
    except Exception as e:
        _log(f"Fetch failed: {e}")
        return []

    models = response if isinstance(response, list) else []
    
    # Calculate date threshold
    date_threshold = None
    if days > 0:
        date_threshold = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    items = []
    for m in models:
        model_id = m.get("modelId", "")
        created_at = m.get("createdAt", "")
        
        # Topic filter (case-insensitive)
        if topic and topic.lower() not in model_id.lower():
            continue
        
        # Date filter
        if date_threshold and created_at:
            if created_at < date_threshold:
                continue

        items.append({
            "model_id": model_id,
            "url": f"https://huggingface.co/{model_id}",
            "downloads": m.get("downloads", 0),
            "likes": m.get("likes", 0),
            "tags": m.get("tags", []),
            "created_at": created_at,
            "source": "huggingface",
        })
        
        if len(items) >= count:
            break

    _log(f"Found {len(items)} models")
    return items


def _format_downloads(downloads: int) -> str:
    """Format download count for display."""
    if downloads >= 1_000_000:
        return f"{downloads / 1_000_000:.1f}M"
    elif downloads >= 1_000:
        return f"{downloads / 1_000:.1f}K"
    return str(downloads)


def parse_huggingface_response(items: List[Dict[str, Any]], query: str = "") -> List[Dict[str, Any]]:
    """Parse HuggingFace items into normalized format.

    Args:
        items: Raw HuggingFace model list
        query: Original search query for relevance scoring

    Returns:
        List of normalized item dicts.
    """
    from .relevance import token_overlap_relevance

    normalized = []
    for i, item in enumerate(items):
        model_id = item.get("model_id", "")
        downloads = item.get("downloads", 0)
        likes = item.get("likes", 0)

        # Relevance: blend rank with downloads/likes
        rank_score = max(0.3, 1.0 - (i * 0.02))
        engagement_boost = min(0.2, math.log1p(downloads) / 20 + math.log1p(likes) / 15)
        if query:
            content_score = token_overlap_relevance(query, model_id)
            relevance = min(1.0, 0.5 * rank_score + 0.35 * content_score + engagement_boost)
        else:
            relevance = min(1.0, rank_score * 0.6 + engagement_boost + 0.1)

        # Extract org from model_id (e.g., "meta-llama/Llama-4" -> "meta-llama")
        org = model_id.split("/")[0] if "/" in model_id else ""

        normalized.append({
            "object_id": model_id.replace("/", "--"),
            "title": model_id,
            "url": item.get("url", f"https://huggingface.co/{model_id}"),
            "author": org,
            "date": item.get("created_at"),
            "engagement": {
                "downloads": downloads,
                "downloads_formatted": _format_downloads(downloads),
                "likes": likes,
                "tags": item.get("tags", [])[:5],  # Top 5 tags
            },
            "relevance": round(relevance, 2),
            "why_relevant": f"HuggingFace model with {_format_downloads(downloads)} downloads",
            "source": "huggingface",
        })

    return normalized