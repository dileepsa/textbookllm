"""In-memory metadata store implementation."""
from __future__ import annotations

from typing import List

from ..contracts import MetadataStore
from ..models import Document, Chunk, IngestionResult


class InMemoryMetadataStore(MetadataStore):
	"""Simple in-memory metadata store."""
	
	def __init__(self) -> None:
		self._documents: dict[str, Document] = {}
		self._chunks: dict[str, Chunk] = {}

	def write_ingestion(self, result: IngestionResult) -> None:
		"""Write ingestion result to the store."""
		self._documents[result.document.id] = result.document
		for c in result.chunks:
			self._chunks[c.id] = c

	def get_document(self, document_id: str) -> Document | None:
		"""Retrieve document metadata by ID."""
		return self._documents.get(document_id)

	def get_chunks(self, chunk_ids: List[str]) -> List[Chunk]:
		"""Retrieve multiple chunks by their IDs."""
		return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

	def list_all_documents(self) -> List[Document]:
		"""List all stored documents."""
		return list(self._documents.values())

	def get_documents_by_filenames(self, filenames: List[str]) -> List[Document]:
		"""Get all documents with the specified filenames."""
		return [doc for doc in self._documents.values() if doc.filename in filenames]

	def delete_document(self, document_id: str) -> bool:
		"""Delete a document and all its chunk metadata."""
		if document_id not in self._documents:
			return False
		# Delete the document
		del self._documents[document_id]
		# Delete all chunks belonging to this document
		chunk_ids_to_delete = [cid for cid, chunk in self._chunks.items() if chunk.document_id == document_id]
		for cid in chunk_ids_to_delete:
			del self._chunks[cid]
		return True

	def get_chunk_ids_by_document(self, document_id: str) -> List[str]:
		"""Get all chunk IDs belonging to a document."""
		return [cid for cid, chunk in self._chunks.items() if chunk.document_id == document_id]

