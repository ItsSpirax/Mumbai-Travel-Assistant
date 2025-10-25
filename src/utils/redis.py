import json
from typing import Tuple, List, Optional

import numpy as np
import torch
from redis.asyncio import Redis as AsyncRedis


async def store_embeddings(
    redis_client: AsyncRedis,
    cache_key: str,
    values: List[str],
    embeddings: torch.Tensor,
):
    """
    Stores line items and their corresponding embeddings in Redis with a 24-hour TTL.
    """
    try:
        pipeline = redis_client.pipeline()
        embeddings_bytes = embeddings.cpu().numpy().tobytes()
        values_json = json.dumps(values)

        pipeline.set(f"values:{cache_key}", values_json, ex=86400)
        pipeline.set(f"embeddings:{cache_key}", embeddings_bytes, ex=86400)
        await pipeline.execute()
        print(f"Cached embeddings for key: {cache_key}")
    except Exception as e:
        print(f"Failed to store embeddings in cache: {e}")


async def get_cached_embeddings(
    redis_client: AsyncRedis, cache_key: str, model
) -> Tuple[Optional[List[str]], Optional[torch.Tensor]]:
    """
    Retrieves and deserializes line items and embeddings from the Redis cache.
    """
    try:
        pipeline = redis_client.pipeline()
        pipeline.get(f"values:{cache_key}")
        pipeline.get(f"embeddings:{cache_key}")
        values_json, embeddings_bytes = await pipeline.execute()

        if not values_json or not embeddings_bytes:
            return (None, None)

        values = json.loads(values_json)

        embedding_dim = model.get_sentence_embedding_dimension()
        num_items = len(values)
        expected_shape = (num_items, embedding_dim)

        embeddings_np = np.frombuffer(embeddings_bytes, dtype=np.float32).reshape(
            expected_shape
        )
        embeddings_tensor = torch.from_numpy(embeddings_np).to(model.device)

        return (values, embeddings_tensor)
    except Exception as e:
        print(f"Error retrieving cached embeddings: {e}")
        return (None, None)
