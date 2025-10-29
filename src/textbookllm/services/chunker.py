"""Text chunking implementations."""
from __future__ import annotations

import uuid
from typing import List

from ..contracts import Chunker
from ..models import Chunk, Document


class SimpleChunker(Chunker):
	"""Simple character-based chunker."""
	
	def __init__(self, max_chars: int = 1000) -> None:
		self._max_chars = max_chars

	def chunk(self, document: Document) -> List[Chunk]:
		"""Split document text into fixed-size chunks."""
		if not document.text_content:
			return []
		text = document.text_content
		chunks: List[Chunk] = []
		order = 0
		for i in range(0, len(text), self._max_chars):
			chunk_text = text[i : i + self._max_chars]
			chunks.append(
				Chunk(
					id=str(uuid.uuid4()),
					document_id=document.id,
					text=chunk_text,
					order=order,
					metadata={"source_type": document.source_type},
				)
			)
			order += 1
		return chunks
