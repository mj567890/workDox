"""Embedding service using fastembed (ONNX Runtime, no PyTorch).

Model: BAAI/bge-small-zh-v1.5 (768 dims, Chinese-optimized).
Lazy-loaded on first use; runs in thread pool to avoid blocking event loop.
"""

import asyncio
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        self._model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from fastembed import TextEmbedding

            logger.info("Loading embedding model: %s", self._model_name)
            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        model = self._load_model()
        embeddings = await asyncio.to_thread(
            lambda: [emb.tolist() for emb in model.embed(texts)]
        )
        return embeddings

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        results = await self.embed([text])
        return results[0]


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
