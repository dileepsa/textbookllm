"""Embedding implementations."""
from __future__ import annotations

import hashlib
from typing import List

from ..contracts import Embedder
from ..models import Embedding


class HashEmbedder(Embedder):
	"""Simple hash-based embedder for testing/demo purposes."""
	
	def __init__(self, dim: int = 256) -> None:
		self._dim = dim

	def embed(self, texts: List[str]) -> List[Embedding]:
		"""Create embeddings using SHA256 hash."""
		embeddings: List[Embedding] = []
		for t in texts:
			h = hashlib.sha256(t.encode("utf-8")).digest()
			# Repeat/truncate to dimension
			vec_bytes = (h * ((self._dim // len(h)) + 1))[: self._dim]
			vec = [b / 255.0 for b in vec_bytes]
			embeddings.append(Embedding(vector=vec, dimension=self._dim))
		return embeddings

	def dimension(self) -> int:
		"""Return embedding dimension."""
		return self._dim
