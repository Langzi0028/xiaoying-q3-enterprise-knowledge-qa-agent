"""Configurable embeddings with deterministic local vector fallback."""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from typing import Any


_DIMENSION = 1024
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)
_FEATURE_HASH_VERSION = "local-feature-hash-v4"


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    mode: str
    model_name: str
    error_type: str | None = None
    diagnostics: dict[str, object] | None = None


class EmbeddingProvider:
    def __init__(
        self,
        *,
        mode: str,
        model_name: str,
        test_response: dict[str, Any] | None = None,
    ) -> None:
        self.mode = mode
        self.model_name = model_name
        self.test_response = test_response

    @classmethod
    def from_environment(cls) -> "EmbeddingProvider":
        values = {
            name: os.getenv(name)
            for name in ("EMBEDDING_API_KEY", "EMBEDDING_BASE_URL", "EMBEDDING_MODEL")
        }
        if all(values.values()):
            return cls(mode="live_embedding", model_name=str(values["EMBEDDING_MODEL"]))
        return cls.hash_fallback()

    @classmethod
    def hash_fallback(
        cls, *, model_name: str = _FEATURE_HASH_VERSION
    ) -> "EmbeddingProvider":
        return cls(mode="hash_fallback", model_name=model_name)

    @classmethod
    def with_test_response(cls, response: dict[str, Any]) -> "EmbeddingProvider":
        return cls(mode="live_embedding", model_name="test-live-model", test_response=response)

    @property
    def fingerprint(self) -> str:
        return f"{self.mode}:{self.model_name}"

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        if self.mode == "hash_fallback":
            return self._hash_batch(texts)
        try:
            if self.test_response is not None:
                vectors = self._validate_response(self.test_response, len(texts))
            else:
                vectors = self._live_request(texts)
            return EmbeddingBatch(
                vectors=vectors,
                mode="live_embedding",
                model_name=self.model_name,
                diagnostics={"vector_count": len(vectors)},
            )
        except Exception as error:
            fallback = self._hash_batch(texts)
            return EmbeddingBatch(
                vectors=fallback.vectors,
                mode="hash_fallback",
                model_name=fallback.model_name,
                error_type=type(error).__name__,
                diagnostics={"vector_count": len(fallback.vectors)},
            )

    def _live_request(self, texts: list[str]) -> list[list[float]]:
        from langchain_openai import OpenAIEmbeddings

        client = OpenAIEmbeddings(
            model=os.environ["EMBEDDING_MODEL"],
            api_key=os.environ["EMBEDDING_API_KEY"],
            base_url=os.environ["EMBEDDING_BASE_URL"],
            request_timeout=15,
        )
        return self._validate_vectors(client.embed_documents(texts), len(texts))

    def _validate_response(self, response: dict[str, Any], expected_count: int) -> list[list[float]]:
        data = response.get("data")
        if not isinstance(data, list):
            raise ValueError("Embedding response has no data list")
        vectors = [item.get("embedding") for item in data if isinstance(item, dict)]
        return self._validate_vectors(vectors, expected_count)

    @staticmethod
    def _validate_vectors(vectors: object, expected_count: int) -> list[list[float]]:
        if not isinstance(vectors, list) or len(vectors) != expected_count:
            raise ValueError("Embedding count mismatch")
        normalized: list[list[float]] = []
        dimension: int | None = None
        for vector in vectors:
            if not isinstance(vector, list) or not vector:
                raise ValueError("Embedding vector missing")
            if not all(isinstance(value, (int, float)) for value in vector):
                raise ValueError("Embedding vector contains non-numeric value")
            if dimension is None:
                dimension = len(vector)
            if len(vector) != dimension:
                raise ValueError("Embedding dimensions differ")
            magnitude = math.sqrt(sum(float(value) ** 2 for value in vector))
            if magnitude == 0:
                raise ValueError("Embedding vector is zero")
            normalized.append([float(value) / magnitude for value in vector])
        return normalized

    def _hash_batch(self, texts: list[str]) -> EmbeddingBatch:
        return EmbeddingBatch(
            vectors=[self._hash_vector(text) for text in texts],
            mode="hash_fallback",
            model_name=self.model_name if self.mode == "hash_fallback" else "local-feature-hash-v1",
            diagnostics={"vector_count": len(texts)},
        )

    @staticmethod
    def _hash_vector(text: str) -> list[float]:
        normalized = "".join(text.lower().split())
        tokens = _TOKEN_PATTERN.findall(normalized)
        # Add compact concept features before hashing. This remains a local
        # vector representation, while making policy synonyms share space.
        if any(token in normalized for token in ("报销", "凭证", "发票", "费用")):
            tokens.extend(["expensepolicy"] * 8)
        if any(token in normalized for token in ("国内", "出差", "差旅")):
            tokens.extend(["domestictravel"] * 30)
        if "普通" in normalized:
            tokens.extend(["ordinarytravel"] * 30)
        if "紧急项目" in normalized:
            tokens.extend(["urgentproject"] * 30)
        if any(token in normalized for token in ("导出", "视频", "creatorhub")):
            tokens.extend(["exportguide"] * 8)
        features = list(tokens)
        features.extend("".join(tokens[index : index + 2]) for index in range(len(tokens) - 1))
        vector = [0.0] * _DIMENSION
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % _DIMENSION
            sign = 1.0 if digest[4] % 2 else -1.0
            vector[bucket] += sign
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector] if magnitude else vector
