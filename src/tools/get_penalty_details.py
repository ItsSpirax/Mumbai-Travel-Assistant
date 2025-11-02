from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

import torch
from sentence_transformers import SentenceTransformer

from app import app_state, mcp
from utils.redis import get_cached_embeddings, store_embeddings


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TRAFFIC_DATA_FILE = DATA_DIR / "traffic_penalties.txt"
RAILWAY_DATA_FILE = DATA_DIR / "railway_penalties.txt"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_KEY = f"penalty_records::{MODEL_NAME}::v1"


@dataclass
class PenaltyRecord:
    code: str
    description: str
    penalty: str
    category: str

    def as_text(self) -> str:
        parts = [self.category, self.code, self.description]
        if self.penalty:
            parts.append(f"Penalty: {self.penalty}")
        return " | ".join(segment for segment in parts if segment)


MODEL: Optional[SentenceTransformer] = None
PENALTY_RECORDS: List[PenaltyRecord] = []
PENALTY_TEXTS: List[str] = []
PENALTY_EMBEDDINGS: Optional[torch.Tensor] = None

VALID_CATEGORIES = {"traffic", "railway", "railway-other"}


def _load_text_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Penalty dataset file missing: {path}")
    return path.read_text(encoding="utf-8").splitlines()


def _parse_traffic_records(lines: Sequence[str]) -> List[PenaltyRecord]:
    records: List[PenaltyRecord] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("traffic penalties"):
            continue
        parts = [part.strip() for part in line.split(",", 2)]
        if len(parts) < 2:
            continue
        code = parts[0]
        description = parts[1]
        penalty = parts[2] if len(parts) == 3 else ""
        records.append(
            PenaltyRecord(
                code=code, description=description, penalty=penalty, category="traffic"
            )
        )
    return records


def _parse_railway_records(lines: Sequence[str]) -> List[PenaltyRecord]:
    records: List[PenaltyRecord] = []
    current_category = "railway"

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        normalized = line.lower()
        if normalized.startswith("railway penalties"):
            continue
        if normalized == "other offences":
            current_category = "railway-other"
            continue

        parts = [part.strip() for part in line.split(",", 2)]
        if len(parts) == 1:
            code, description, penalty = "", parts[0], ""
        else:
            code = parts[0]
            description = parts[1] if len(parts) > 1 else ""
            penalty = parts[2] if len(parts) > 2 else ""

        if not description and code:
            description = code
            code = ""

        if not description:
            continue

        records.append(
            PenaltyRecord(
                code=code,
                description=description,
                penalty=penalty,
                category=current_category,
            )
        )

    return records


def _ensure_records_loaded() -> None:
    global PENALTY_RECORDS, PENALTY_TEXTS

    if PENALTY_RECORDS:
        return

    traffic_lines = _load_text_file(TRAFFIC_DATA_FILE)
    railway_lines = _load_text_file(RAILWAY_DATA_FILE)

    records = _parse_traffic_records(traffic_lines)
    records.extend(_parse_railway_records(railway_lines))

    if not records:
        raise RuntimeError("Failed to load any penalty records from datasets")

    PENALTY_RECORDS = records
    PENALTY_TEXTS = [record.as_text() for record in PENALTY_RECORDS]


async def _load_model() -> SentenceTransformer:
    global MODEL
    if MODEL is None:
        MODEL = await asyncio.to_thread(SentenceTransformer, MODEL_NAME)
    return MODEL


async def _compute_embeddings(
    model: SentenceTransformer, texts: Sequence[str]
) -> torch.Tensor:
    if not texts:
        raise ValueError("No texts provided for embedding computation")

    embeddings: torch.Tensor = await asyncio.to_thread(
        model.encode,
        list(texts),
        convert_to_tensor=True,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.to(model.device)


async def ensure_penalty_embeddings(force: bool = False) -> None:
    global PENALTY_EMBEDDINGS

    _ensure_records_loaded()

    if PENALTY_EMBEDDINGS is not None and not force:
        return

    model = await _load_model()

    redis_client = app_state.redis_client
    if not force and redis_client is not None:
        cached_values, cached_embeddings = await get_cached_embeddings(
            redis_client, CACHE_KEY, model
        )
        if cached_values and cached_embeddings is not None:
            if (
                len(cached_values) == len(PENALTY_TEXTS)
                and cached_values == PENALTY_TEXTS
            ):
                PENALTY_EMBEDDINGS = cached_embeddings
                return

    embeddings = await _compute_embeddings(model, PENALTY_TEXTS)
    PENALTY_EMBEDDINGS = embeddings

    if redis_client is not None:
        await store_embeddings(redis_client, CACHE_KEY, PENALTY_TEXTS, embeddings)


def _select_indices(category: Optional[str]) -> List[int]:
    if not category:
        return list(range(len(PENALTY_RECORDS)))

    normalized = category.strip().lower()
    if normalized not in VALID_CATEGORIES and normalized != "railway":
        raise ValueError(
            f"category must be one of {sorted(VALID_CATEGORIES)} or 'railway'"
        )

    if normalized == "railway":
        targets = {"railway", "railway-other"}
    else:
        targets = {normalized}

    return [
        idx for idx, record in enumerate(PENALTY_RECORDS) if record.category in targets
    ]


def _format_record(record: PenaltyRecord, similarity: float) -> dict:
    return {
        "code": record.code or None,
        "description": record.description or None,
        "penalty": record.penalty or None,
        "category": record.category,
        "similarity": round(float(similarity), 4),
    }


@mcp.tool(name="penalty_semantic_lookup")
async def penalty_semantic_lookup(
    query: str, top_k: int = 5, category: Optional[str] = None
) -> dict:
    """
    Perform semantic search across Mumbai traffic and railway penalty regulations.

    **TOOL SIGNATURE:**
    ```python
    penalty_semantic_lookup(
            query: str,                                    # Search query (required)
            top_k: int = 5,                               # Max results (must be > 0)
            category: Optional[Literal["traffic", "railway", "railway-other"]] = None
    ) -> Dict[str, Any]
    ```

    **PARAMETERS:**
    - query (str): Natural language search query (required, cannot be empty)
    - top_k (int): Maximum number of results to return (must be > 0)
    - category (str, optional): Filter by category:
            * "traffic" - Road traffic violations
            * "railway" - Railway passenger violations
            * "railway-other" - Other railway offences
            * None - Search all categories

    **RETURNS:**
    Dict[str, Any]:
    {
            "query": str,
            "category": str,  # Applied category or "all"
            "matched": int,   # Number of results returned
            "total_candidates": int,  # Total entries searched
            "results": [
                    {
                            "code": Optional[str],        # Violation code
                            "description": str,           # Violation description
                            "penalty": Optional[str],     # Penalty amount/details
                            "category": str,              # Record category
                            "similarity": float           # Cosine similarity score (0-1)
                    }
            ],
            "notes": Optional[str]  # If no results found
    }

    **USAGE EXAMPLES:**

    Example 1 - General traffic query:
    ```python
    result = await penalty_semantic_lookup(
            query="parking in no parking zone",
            top_k=3
    )
    # Returns top 3 parking-related violations
    ```

    Example 2 - Specific traffic violation:
    ```python
    result = await penalty_semantic_lookup(
            query="riding without helmet",
            category="traffic",
            top_k=5
    )
    # Search only traffic penalties
    ```

    Example 3 - Railway violations:
    ```python
    result = await penalty_semantic_lookup(
            query="travelling without ticket",
            category="railway",
            top_k=3
    )
    # Returns ticketless travel penalties
    ```

    Example 4 - Complex query:
    ```python
    result = await penalty_semantic_lookup(
            query="what is the fine for jumping red light",
            top_k=5
    )
    # Semantic matching handles natural language
    ```

    Example 5 - Broad search:
    ```python
    result = await penalty_semantic_lookup(
            query="drunk driving penalties",
            top_k=10
    )
    # Returns all related violations
    ```

    **SIMILARITY SCORING:**
    - 1.0: Perfect match
    - 0.8-1.0: High relevance
    - 0.6-0.8: Moderate relevance
    - <0.6: Low relevance

    Results are sorted by similarity score (highest first).

    **SEMANTIC FEATURES:**
    - Handles typos and variations
    - Understands synonyms (e.g., "bike" = "motorcycle")
    - Matches intent, not just keywords
    - Works with natural questions

    **PERFORMANCE:**
    - Embeddings cached in Redis for fast queries
    - First query may be slower (model initialization)
    - Subsequent queries are near-instant

    **ERROR CONDITIONS:**
    - ValueError: Empty query string
    - ValueError: top_k <= 0
    - ValueError: Invalid category value
    - RuntimeError: Embedding initialization failure
    """

    if not query or not query.strip():
        raise ValueError("query cannot be empty")
    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    await ensure_penalty_embeddings()

    if PENALTY_EMBEDDINGS is None:
        raise RuntimeError("Penalty embeddings are not initialized")

    model = await _load_model()

    indices = _select_indices(category)
    if not indices:
        return {
            "query": query,
            "category": category or "all",
            "results": [],
            "notes": "No penalty entries available for the requested category.",
        }

    embeddings_subset = PENALTY_EMBEDDINGS[indices]

    query_embedding = await asyncio.to_thread(
        model.encode,
        [query],
        convert_to_tensor=True,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    query_vector = query_embedding[0].to(embeddings_subset.device)

    scores = torch.matmul(embeddings_subset, query_vector)

    k = min(top_k, len(indices))
    top_scores, top_indices = torch.topk(scores, k=k)

    results = [
        _format_record(PENALTY_RECORDS[indices[result_idx]], top_scores[idx].item())
        for idx, result_idx in enumerate(top_indices.tolist())
    ]

    return {
        "query": query,
        "category": category or "all",
        "matched": len(results),
        "total_candidates": len(indices),
        "results": results,
    }
