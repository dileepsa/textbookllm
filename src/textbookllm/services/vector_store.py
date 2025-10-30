"""In-memory vector store implementation."""
from __future__ import annotations

from typing import List, Tuple

from ..contracts import VectorStore
from ..models import Chunk, Embedding


class InMemoryVectorStore(VectorStore):
	"""Simple in-memory vector store with cosine similarity search."""
	
	def __init__(self) -> None:
		self._store: List[Tuple[str, List[float], Chunk]] = []

	def upsert(self, ids: List[str], embeddings: List[Embedding], metadatas: List[Chunk]) -> None:
		"""Insert or update vectors."""
		for i, emb, meta in zip(ids, embeddings, metadatas):
			self._store = [row for row in self._store if row[0] != i]
			self._store.append((i, emb.vector, meta))

	def delete(self, ids: List[str]) -> None:
		"""Delete vectors by their IDs."""
		ids_set = set(ids)
		self._store = [row for row in self._store if row[0] not in ids_set]

	def _cosine(self, a: List[float], b: List[float]) -> float:
		"""Calculate cosine similarity between two vectors."""
		if not a or not b:
			return 0.0
		num = sum(x * y for x, y in zip(a, b))
		den_a = sum(x * x for x in a) ** 0.5
		den_b = sum(y * y for y in b) ** 0.5
		if den_a == 0.0 or den_b == 0.0:
			return 0.0
		return num / (den_a * den_b)

	def search(self, embedding: Embedding, k: int) -> List[Tuple[str, float]]:
		"""Search for similar vectors using cosine similarity."""
		scores = [(cid, self._cosine(embedding.vector, vec)) for cid, vec, _ in self._store]
		scores.sort(key=lambda x: x[1], reverse=True)
		return scores[:k]
