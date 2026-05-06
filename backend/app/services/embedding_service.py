"""Embedding service using fastembed (ONNX Runtime, no PyTorch).

Model: BAAI/bge-small-zh-v1.5 (512 dims, Chinese-optimized).
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
        self._load_error: str | None = None

    def _load_model(self):
        if self._model is None and self._load_error is None:
            from fastembed import TextEmbedding

            logger.info("Loading embedding model: %s", self._model_name)
            try:
                self._model = TextEmbedding(model_name=self._model_name)
            except Exception as e:
                self._load_error = f"Failed to load embedding model {self._model_name}: {e}"
                logger.exception(self._load_error)
                raise RuntimeError(self._load_error) from e

        if self._load_error:
            raise RuntimeError(self._load_error)

        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Raises RuntimeError if model failed to load.
        Returns zero-vectors on per-text encoding failure so the batch isn't lost.
        """
        if not texts:
            return []

        model = self._load_model()

        def _encode():
            try:
                return [emb.tolist() for emb in model.embed(texts)]
            except Exception:
                logger.exception("Embedding generation failed for %d texts", len(texts))
                raise

        try:
            embeddings = await asyncio.to_thread(_encode)
        except Exception:
            # Fall back to zero-vectors so callers don't crash
            # Try to detect dimension from a test encode, or default to 512
            try:
                test_emb = await asyncio.to_thread(
                    lambda: model.embed(["test"])[0].tolist()
                )
                dims = len(test_emb)
            except Exception:
                dims = 512
            logger.warning("Returning zero-vectors of dim %d due to embedding failure", dims)
            embeddings = [[0.0] * dims for _ in texts]

        return embeddings

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        results = await self.embed([text])
        return results[0]


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
