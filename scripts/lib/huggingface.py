"""HuggingFace models fetcher - Popular AI models from huggingface.co.

Uses HuggingFace public API to fetch trending models.
No API key required.

Quality signal: likes-to-downloads ratio indicates model quality vs hype.
A model with high downloads but low likes may be widely used but not well-regarded.
A model with high likes relative to downloads indicates strong community approval.
"""

import math
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from . import http

HF_MODELS_URL = "https://huggingface.co/api/models"

DEPTH_CONFIG = {
    "quick": 15,
    "default": 30,
    "deep": 50,
}

# Quality ratio thresholds (likes/downloads percentage)
QUALITY_HIGH = 0.05    # 5%+ likes/downloads = high quality
QUALITY_MEDIUM = 0.02  # 2%+ likes/downloads = medium quality
QUALITY_LOW = 0.005    # 0.5%+ likes/downloads = acceptable


def _log(msg: str):
    """Log to stderr (only in TTY mode to avoid cluttering Claude Code output)."""
    if sys.stderr.isatty():
        sys.stderr.write(f"[HuggingFace] {msg}\n")
        sys.stderr.flush()


def _calculate_quality_ratio(likes: int, downloads: int) -> float:
    """Calculate likes-to-downloads ratio as a quality signal.
    
    Returns a value between 0 and 1, where higher is better.
    Uses log scale to handle the wide range of values.
    
    Args:
        likes: Number of likes
        downloads: Number of downloads
        
    Returns:
        Quality ratio (0.0 to 1.0)
    """
    if downloads == 0:
        return 0.0
    
    raw_ratio = likes / downloads
    
    # Use log scale for scoring
    # A 10% ratio (0.1) should score very high
    # A 0.1% ratio (0.001) should score low
    if raw_ratio >= QUALITY_HIGH:
        return min(1.0, 0.7 + (raw_ratio - QUALITY_HIGH) * 3)
    elif raw_ratio >= QUALITY_MEDIUM:
        return 0.5 + (raw_ratio - QUALITY_MEDIUM) / (QUALITY_HIGH - QUALITY_MEDIUM) * 0.2
    elif raw_ratio >= QUALITY_LOW:
        return 0.3 + (raw_ratio - QUALITY_LOW) / (QUALITY_MEDIUM - QUALITY_LOW) * 0.2
    else:
        return raw_ratio / QUALITY_LOW * 0.3


def _get_quality_label(ratio: float) -> str:
    """Get quality label based on ratio."""
    if ratio >= 0.7:
        return "⭐ excellent"
    elif ratio >= 0.5:
        return "👍 good"
    elif ratio >= 0.3:
        return "✓ acceptable"
    else:
        return ""


def fetch_huggingface_models(
    topic: Optional[str] = None,
    depth: str = "default",
    days: int = 0,  # Changed default to 0 (no date filter) - popular models are often older
) -> List[Dict[str, Any]]:
    """Fetch popular models from HuggingFace.

    Args:
        topic: Optional topic filter (case-insensitive substring match on model ID)
        depth: 'quick', 'default', or 'deep'
        days: Only include models from last N days (0 = no filter, default)

    Returns:
        List of model dicts with modelId, downloads, likes, tags, quality_ratio.
    """
    count = DEPTH_CONFIG.get(depth, DEPTH_CONFIG["default"])
    _log(f"Fetching {count} models" + (f" (filter: {topic})" if topic else ""))

    params = {
        "sort": "downloads",
        "direction": -1,
        "limit": count * 2,  # Fetch more to filter later
    }
    
    url = f"{HF_MODELS_URL}?{urlencode(params)}"

    try:
        response = http.request("GET", url, timeout=30)
    except Exception as e:
        _log(f"Fetch failed: {e}")
        return []

    models = response if isinstance(response, list) else []
    
    items = []
    for m in models:
        model_id = m.get("modelId", "")
        
        # Topic filter (case-insensitive)
        if topic and topic.lower() not in model_id.lower():
            continue

        downloads = m.get("downloads", 0)
        likes = m.get("likes", 0)
        quality_ratio = _calculate_quality_ratio(likes, downloads)

        items.append({
            "model_id": model_id,
            "url": f"https://huggingface.co/{model_id}",
            "downloads": downloads,
            "likes": likes,
            "quality_ratio": quality_ratio,
            "quality_label": _get_quality_label(quality_ratio),
            "tags": m.get("tags", []),
            "created_at": m.get("createdAt", ""),
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


def _format_ratio(ratio: float) -> str:
    """Format quality ratio for display."""
    return f"{ratio * 100:.1f}%"


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
        quality_ratio = item.get("quality_ratio", 0.0)
        quality_label = item.get("quality_label", "")

        # Relevance: blend rank with downloads/likes/quality
        rank_score = max(0.3, 1.0 - (i * 0.02))
        
        # Engagement boost: downloads + likes + quality ratio
        engagement_boost = min(0.15, math.log1p(downloads) / 25 + math.log1p(likes) / 20)
        
        # Quality boost: high quality models get extra relevance
        quality_boost = quality_ratio * 0.1
        
        if query:
            content_score = token_overlap_relevance(query, model_id)
            relevance = min(1.0, 0.5 * rank_score + 0.3 * content_score + engagement_boost + quality_boost)
        else:
            relevance = min(1.0, rank_score * 0.5 + engagement_boost + quality_boost + 0.2)

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
                "quality_ratio": round(quality_ratio, 3),
                "quality_ratio_formatted": _format_ratio(quality_ratio),
                "quality_label": quality_label,
                "tags": item.get("tags", [])[:5],  # Top 5 tags
            },
            "relevance": round(relevance, 2),
            "why_relevant": f"HuggingFace model with {_format_downloads(downloads)} downloads" + (f" ({quality_label})" if quality_label else ""),
            "source": "huggingface",
        })

    return normalized