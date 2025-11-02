from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app import app_state, mcp


REDDIT_SEARCH_URL = "https://www.reddit.com/r/Mumbai/search.json"
DEFAULT_QUERY = "subreddit:Mumbai selftext:Traffic"
USER_AGENT = "MumbaiTravelAssistant/1.0 (by u/mumbai-travel-assistant)"

POSITIVE_KEYWORDS = {
    "clear",
    "improve",
    "lighter",
    "moving",
    "open",
    "smooth",
    "stable",
}

NEGATIVE_KEYWORDS = {
    "accident",
    "blocked",
    "breakdown",
    "chaos",
    "congestion",
    "delay",
    "gridlock",
    "jam",
    "jammed",
    "slow",
    "stalled",
    "traffic",
    "unsafe",
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _score_sentiment(content: str) -> Dict[str, Any]:
    tokens = _tokenize(content)
    positive_hits = sum(1 for token in tokens if token in POSITIVE_KEYWORDS)
    negative_hits = sum(1 for token in tokens if token in NEGATIVE_KEYWORDS)
    raw_score = positive_hits - negative_hits
    magnitude = positive_hits + negative_hits
    if raw_score > 1:
        label = "positive"
    elif raw_score < -1:
        label = "negative"
    else:
        label = "neutral"
    confidence = 0.0 if magnitude == 0 else min(1.0, magnitude / 6.0)
    return {
        "label": label,
        "score": raw_score,
        "confidence": round(confidence, 2),
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
    }


def _select_client() -> httpx.AsyncClient:
    if app_state.http_client is None:
        app_state.http_client = httpx.AsyncClient(timeout=30.0)
    return app_state.http_client


async def _fetch_comments(
    post_id: str, client: httpx.AsyncClient, limit: int = 10
) -> List[Dict[str, Any]]:
    """Fetch top comments for a given post."""
    url = f"https://www.reddit.com/comments/{post_id}.json"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        response = await client.get(url, params={"limit": limit}, headers=headers)
        response.raise_for_status()
        data = response.json()

        if len(data) < 2:
            return []

        comments_data = data[1].get("data", {}).get("children", [])
        comments = []

        for comment in comments_data[:limit]:
            comment_data = comment.get("data", {})
            if comment_data.get("kind") == "more":
                continue

            body = comment_data.get("body", "")
            if body:
                created_utc = comment_data.get("created_utc")
                created_at = None
                if isinstance(created_utc, (int, float)):
                    created_at = datetime.fromtimestamp(
                        created_utc, tz=timezone.utc
                    ).isoformat()

                comments.append(
                    {
                        "id": comment_data.get("id"),
                        "author": comment_data.get("author"),
                        "body": body,
                        "score": comment_data.get("score", 0),
                        "created_at": created_at,
                    }
                )

        return comments
    except Exception:
        return []


@mcp.tool(name="traffic_sentiment_search")
async def traffic_sentiment_search(
    query: Optional[str] = None,
    limit: int = 5,
    sort: str = "new",
    include_comments: bool = True,
) -> Dict[str, Any]:
    """
    Retrieve Mumbai traffic chatter from Reddit's public JSON search API and classify each post.

    **DISCLAIMER:** This tool provides a sentiment-based summary of traffic discussions on Reddit. It is NOT a real-time traffic monitoring service. The sentiment analysis is a heuristic and may not accurately reflect actual road conditions. Use the returned data, including post content (title, body), to make an informed judgment rather than relying solely on the sentiment score.

    **TOOL SIGNATURE:**
    ```python
    traffic_sentiment_search(
        query: Optional[str] = None,
        limit: int = 5,                          # Max 25
        sort: Literal["new", "relevance", "top"] = "new",
        include_comments: bool = True            # Fetch top 10 comments per post
    ) -> Dict[str, Any]
    ```

    **PARAMETERS:**
    - query (str, optional): Custom search query (default: "subreddit:Mumbai selftext:Traffic")
    - limit (int): Max posts to return after 24h filtering (default 5, max 25, must be > 0)
    - sort (str): Reddit sort strategy - "new", "relevance", or "top"
    - include_comments (bool): Whether to fetch top 10 comments for each post (default True)

    **RETURNS:**
    Dict[str, Any]:
    {
        "metadata": {
            "source": str,           # Reddit API URL
            "retrieved_at": str,     # ISO 8601 UTC
            "query": str,            # Applied search query
            "sort": str,
            "total_returned": int
        },
        "summary": {
            "average_sentiment_score": float,  # -N to +N
            "sentiment_bias": str,              # "positive", "negative", "mixed"
            "no_recent_posts": bool
        },
        "posts": [
            {
                "id": str,
                "title": str,
                "body": str,             # Post selftext/description
                "permalink": str,         # Relative URL
                "url": str,              # Full URL
                "created_at": str,       # ISO 8601 UTC
                "age_hours": float,
                "score": int,            # Reddit upvotes
                "num_comments": int,
                "author": str,
                "sentiment": {
                    "label": str,        # "positive", "negative", "neutral"
                    "score": int,        # Raw sentiment score
                    "confidence": float, # 0-1
                    "positive_hits": int,
                    "negative_hits": int
                },
                "over_18": bool,
                "comments": [            # Top 10 comments (if include_comments=True)
                    {
                        "id": str,
                        "author": str,
                        "body": str,
                        "score": int,
                        "created_at": str
                    }
                ]
            }
        ]
    }

    **USAGE EXAMPLES:**

    Example 1 - Recent traffic updates with comments:
    ```python
    result = await traffic_sentiment_search(limit=10)
    # Returns 10 most recent posts with top 10 comments each
    for post in result["posts"]:
        print(f"Post: {post['title']}")
        print(f"Description: {post['body']}")
        for comment in post["comments"]:
            print(f"  - {comment['author']}: {comment['body']}")
    ```

    Example 2 - Posts without comments:
    ```python
    result = await traffic_sentiment_search(limit=5, include_comments=False)
    # Faster response, no comments fetched
    ```

    **SENTIMENT ANALYSIS:**
    Positive keywords: clear, improve, lighter, moving, open, smooth, stable
    Negative keywords: accident, blocked, chaos, congestion, delay, gridlock, jam, slow

    - Positive score: More positive than negative keywords
    - Negative score: More negative than positive keywords
    - Neutral: Balanced or minimal sentiment words

    Confidence: Based on total sentiment keywords found (0-1 scale)

    **INTERPRETATION:**
    - average_sentiment_score > 1: Generally positive conditions
    - average_sentiment_score < -1: Generally negative conditions
    - sentiment_bias: Overall trend across all posts
    - no_recent_posts=true: No traffic posts in last 24 hours

    **TIME FILTERING:**
    - Only includes posts from last 24 hours
    - Posts sorted by created_at (newest first)
    - age_hours shows exact post age

    **ERROR CONDITIONS:**
    - ValueError: limit <= 0
    - Network error: Returns error dict with details
    - Invalid JSON: Returns error dict with parsing info
    """

    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    limit = min(limit, 25)

    params = {
        "q": query or DEFAULT_QUERY,
        "restrict_sr": "on",
        "sort": sort,
        "t": "day",
        "limit": max(25, limit * 4),
    }

    client = _select_client()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    try:
        response = await client.get(REDDIT_SEARCH_URL, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        return {
            "error": "Unable to reach Reddit",
            "details": str(exc),
            "source": REDDIT_SEARCH_URL,
        }
    except ValueError as exc:
        return {
            "error": "Unexpected response payload",
            "details": str(exc),
            "source": REDDIT_SEARCH_URL,
        }

    now = datetime.now(timezone.utc)
    twenty_four_hours_ago = now - timedelta(hours=24)
    posts: List[Dict[str, Any]] = []

    children = data.get("data", {}).get("children", [])

    for child in children:
        payload = child.get("data", {})
        created_utc = payload.get("created_utc")
        if not isinstance(created_utc, (int, float)):
            continue
        created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        if created_at < twenty_four_hours_ago:
            continue

        title = payload.get("title", "")
        body = payload.get("selftext", "")
        sentiment = _score_sentiment(f"{title}\n{body}")
        age_delta = now - created_at
        age_hours = round(age_delta.total_seconds() / 3600.0, 2)

        post_dict = {
            "id": payload.get("id"),
            "title": title,
            "body": body,
            "permalink": payload.get("permalink"),
            "url": payload.get("url"),
            "created_at": created_at.isoformat(),
            "age_hours": age_hours,
            "score": payload.get("score"),
            "num_comments": payload.get("num_comments"),
            "author": payload.get("author"),
            "sentiment": sentiment,
            "over_18": payload.get("over_18", False),
        }

        posts.append(post_dict)

    posts.sort(key=lambda item: item["created_at"], reverse=True)
    posts = posts[:limit]

    # Fetch comments for each post if requested
    if include_comments:
        for post in posts:
            post["comments"] = await _fetch_comments(post["id"], client, limit=10)
    else:
        for post in posts:
            post["comments"] = []

    if posts:
        average_score = sum(post["sentiment"]["score"] for post in posts) / len(posts)
    else:
        average_score = 0.0

    return {
        "metadata": {
            "source": REDDIT_SEARCH_URL,
            "retrieved_at": now.isoformat(),
            "query": params["q"],
            "sort": sort,
            "total_returned": len(posts),
        },
        "summary": {
            "average_sentiment_score": round(average_score, 2),
            "sentiment_bias": (
                "positive"
                if average_score > 1
                else "negative" if average_score < -1 else "mixed"
            ),
            "no_recent_posts": len(posts) == 0,
        },
        "posts": posts,
    }
