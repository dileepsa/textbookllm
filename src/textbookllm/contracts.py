from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Tuple

from .models import Chunk, Document, Embedding, IngestionResult, QueryRequest, QueryResponse


class FileLoader(ABC):
	@abstractmethod
	def can_load(self, mime_type: str) -> bool:  # e.g., "application/pdf"
		...

	@abstractmethod
	def load(self, source_path: str, *, mime_type: Optional[str] = None) -> bytes:
		...


class DocumentParser(ABC):
	@abstractmethod
	def supports(self, source_path: str) -> bool:
		...

	@abstractmethod
	def parse(self, source_path: str, payload: bytes) -> Document:
		...


class Chunker(ABC):
	@abstractmethod
	def chunk(self, document: Document) -> List[Chunk]:
		...


class Embedder(ABC):
	@abstractmethod
	def embed(self, texts: List[str]) -> List[Embedding]:
		...

	@abstractmethod
	def dimension(self) -> int:
		...


class VectorStore(ABC):
	@abstractmethod
	def upsert(self, ids: List[str], embeddings: List[Embedding], metadatas: List[Chunk]) -> None:
		...

	@abstractmethod
	def search(self, embedding: Embedding, k: int) -> List[Tuple[str, float]]:
		"""Return list of (chunk_id, score). Higher score = more similar."""
		...

	@abstractmethod
	def delete(self, ids: List[str]) -> None:
		"""Delete vectors by their IDs."""
		...


class MetadataStore(ABC):
	@abstractmethod
	def write_ingestion(self, result: IngestionResult) -> None:
		...

	@abstractmethod
	def get_document(self, document_id: str) -> Optional[Document]:
		...

	@abstractmethod
	def get_chunks(self, chunk_ids: Iterable[str]) -> List[Chunk]:
		...

	@abstractmethod
	def list_all_documents(self) -> List[Document]:
		"""Return all stored documents."""
		...

	@abstractmethod
	def get_documents_by_filenames(self, filenames: List[str]) -> List[Document]:
		"""Return documents matching the given filenames."""
		...

	@abstractmethod
	def delete_document(self, document_id: str) -> bool:
		"""Delete a document and return True if successful."""
		...

	@abstractmethod
	def get_chunk_ids_by_document(self, document_id: str) -> List[str]:
		"""Get all chunk IDs belonging to a document."""
		...


class Retriever(ABC):
	@abstractmethod
	def retrieve(self, request: QueryRequest) -> List[Tuple[Chunk, float]]:
		...


class LLMClient(ABC):
	@abstractmethod
	def generate(self, prompt: str) -> str:
		...


class Pipeline(ABC):
	@abstractmethod
	def ingest(self, source_path: str, *, mime_type: Optional[str] = None) -> IngestionResult:
		...

	@abstractmethod
	def query(self, request: QueryRequest) -> QueryResponse:
		...

	@abstractmethod
	def delete_document(self, document_id: str) -> bool:
		"""Delete a document and its chunks. Return True if successful."""
		...
