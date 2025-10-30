"""Default pipeline implementation with in-memory stores."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

from ..contracts import LLMClient, Pipeline
from ..models import Chunk, Document, IngestionResult, QueryRequest, QueryResponse, RetrievedChunk, SourceType
from .gemini import GeminiClient
from .chromadb_store import ChromaDBVectorStore, ChromaDBMetadataStore
from .chunker import SimpleChunker
from .embedder import HashEmbedder
from .retriever import SimpleRetriever
from .llm import EchoLLM

# Load .env file from project root
_env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(_env_path)


class DefaultPipeline(Pipeline):
	"""Default pipeline with in-memory stores and Gemini LLM support."""

	def __init__(self) -> None:
		"""Initialize pipeline with default components.
		
		Uses Gemini if GEMINI_API_KEY is set, otherwise falls back to EchoLLM.
		"""
		self.metadata = ChromaDBMetadataStore()
		self.chunker = SimpleChunker()
		self.embedder = HashEmbedder()
		self.vector_store = ChromaDBVectorStore()
		self.retriever = SimpleRetriever(self.vector_store, self.embedder, self.metadata)
		
		# Use Gemini if API key is available, otherwise fallback to EchoLLM
		if os.environ.get("GEMINI_API_KEY"):
			self.llm: LLMClient = GeminiClient()
		else:
			self.llm = EchoLLM()

	def ingest(self, source_path: str, *, mime_type: str | None = None) -> IngestionResult:
		"""Ingest a document from file path.
		
		Args:
			source_path: Path to the file.
			mime_type: Optional MIME type hint (currently unused).
			
		Returns:
			Ingestion result with document and chunks.
			
		Raises:
			FileNotFoundError: If source_path doesn't exist.
		"""
		if not os.path.exists(source_path):
			raise FileNotFoundError(f"File not found: {source_path}")
		
		with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
			text = f.read()
		
		# Extract filename from path
		filename = os.path.basename(source_path)
		
		doc = Document(
			id=str(uuid.uuid4()),
			source_type=SourceType.PLAIN,
			source_path=source_path,
			filename=filename,
			metadata={},
			text_content=text,
		)
		
		chunks = self.chunker.chunk(doc)
		embeddings = self.embedder.embed([c.text for c in chunks])
		self.vector_store.upsert([c.id for c in chunks], embeddings, chunks)
		
		result = IngestionResult(document=doc, chunks=chunks, num_chunks=len(chunks))
		self.metadata.write_ingestion(result)
		return result

	def query(self, request: QueryRequest) -> QueryResponse:
		"""Process a query and return response.
		
		Args:
			request: Query request with question and max_results.
			
		Returns:
			Query response with answer and retrieved chunks.
		"""
		pairs: List[Tuple[Chunk, float]] = self.retriever.retrieve(request)
		
		context = "\n\n".join(c.text for c, _ in pairs)
		prompt = (
			f"Answer the user using the context below. "
			f"If unsure, say you don't know.\n\nContext:\n{context}\n\n"
			f"Question: {request.query}\nAnswer:"
		)
		
		answer = self.llm.generate(prompt)
		retrieved = [RetrievedChunk(chunk=c, score=s) for c, s in pairs]
		
		return QueryResponse(
			answer=answer,
			retrieved=retrieved,
			source_documents=[],
			llm_metadata={}
		)

	def delete_document(self, document_id: str) -> bool:
		"""Delete a document and all its chunks from both metadata and vector stores.
		
		Args:
			document_id: ID of the document to delete.
			
		Returns:
			True if deleted successfully, False otherwise.
		"""
		# Get all chunk IDs for this document
		chunk_ids = self.metadata.get_chunk_ids_by_document(document_id)
		
		# Delete from vector store
		if chunk_ids:
			self.vector_store.delete(chunk_ids)
		
		# Delete from metadata store
		return self.metadata.delete_document(document_id)

