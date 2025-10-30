from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path  
from typing import List, Tuple

from dotenv import load_dotenv

from ..contracts import Chunker, Embedder, LLMClient, MetadataStore, Pipeline, Retriever, VectorStore
from ..models import Chunk, Document, Embedding, IngestionResult, QueryRequest, QueryResponse, RetrievedChunk, SourceType
from .gemini import GeminiClient
from .multimedia import MultimediaProcessor

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


class SimpleChunker(Chunker):
	def __init__(self, max_chars: int = 1000) -> None:
		self._max_chars = max_chars

	def chunk(self, document: Document) -> List[Chunk]:
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


class HashEmbedder(Embedder):
	def __init__(self, dim: int = 256) -> None:
		self._dim = dim

	def embed(self, texts: List[str]) -> List[Embedding]:
		embeddings: List[Embedding] = []
		for t in texts:
			h = hashlib.sha256(t.encode("utf-8")).digest()
			# Repeat/truncate to dimension
			vec_bytes = (h * ((self._dim // len(h)) + 1))[: self._dim]
			vec = [b / 255.0 for b in vec_bytes]
			embeddings.append(Embedding(vector=vec, dimension=self._dim))
		return embeddings

	def dimension(self) -> int:
		return self._dim


class InMemoryVectorStore(VectorStore):
	def __init__(self) -> None:
		self._store: List[Tuple[str, List[float], Chunk]] = []

	def upsert(self, ids: List[str], embeddings: List[Embedding], metadatas: List[Chunk]) -> None:
		for i, emb, meta in zip(ids, embeddings, metadatas):
			self._store = [row for row in self._store if row[0] != i]
			self._store.append((i, emb.vector, meta))

	def _cosine(self, a: List[float], b: List[float]) -> float:
		if not a or not b:
			return 0.0
		num = sum(x * y for x, y in zip(a, b))
		den_a = sum(x * x for x in a) ** 0.5
		den_b = sum(y * y for y in b) ** 0.5
		if den_a == 0.0 or den_b == 0.0:
			return 0.0
		return num / (den_a * den_b)

	def search(self, embedding: Embedding, k: int) -> List[Tuple[str, float]]:
		scores = [(cid, self._cosine(embedding.vector, vec)) for cid, vec, _ in self._store]
		scores.sort(key=lambda x: x[1], reverse=True)
		return scores[:k]


class InMemoryMetadataStore(MetadataStore):
	def __init__(self) -> None:
		self._documents: dict[str, Document] = {}
		self._chunks: dict[str, Chunk] = {}

	def write_ingestion(self, result: IngestionResult) -> None:
		self._documents[result.document.id] = result.document
		for c in result.chunks:
			self._chunks[c.id] = c

	def get_document(self, document_id: str) -> Document | None:
		return self._documents.get(document_id)

	def get_chunks(self, chunk_ids: List[str]) -> List[Chunk]:
		return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]


class SimpleRetriever(Retriever):
	def __init__(self, vector_store: VectorStore, embedder: Embedder, metadata: InMemoryMetadataStore) -> None:
		self._vs = vector_store
		self._embed = embedder
		self._meta = metadata

	def retrieve(self, request: QueryRequest) -> List[Tuple[Chunk, float]]:
		[q_emb] = self._embed.embed([request.query])
		hits = self._vs.search(q_emb, request.max_results)
		chunks = self._meta.get_chunks([cid for cid, _ in hits])
		score_map = {cid: score for cid, score in hits}
		return [(c, score_map.get(c.id, 0.0)) for c in chunks]


class EchoLLM(LLMClient):
	def generate(self, prompt: str) -> str:
		return prompt


class DefaultPipeline(Pipeline):
	def __init__(self, use_base64_multimedia: bool = False) -> None:
		self.metadata = InMemoryMetadataStore()
		self.chunker = SimpleChunker()
		self.embedder = HashEmbedder()
		self.vector_store = InMemoryVectorStore()
		self.retriever = SimpleRetriever(self.vector_store, self.embedder, self.metadata)
		
		# Initialize multimedia processor with BASE64 option
		self.multimedia_processor = MultimediaProcessor(use_base64=use_base64_multimedia)
	
		if os.environ.get("GEMINI_API_KEY"):
			print("[DEBUG] Initializing GeminiClient...")
			self.llm = GeminiClient()
			print(f"[DEBUG] GeminiClient initialized. Model configured: {self.llm._model is not None}")
		else:
			print("[DEBUG] GEMINI_API_KEY not found. Using EchoLLM fallback.")
			self.llm = EchoLLM()

	def ingest(self, source_path: str, *, mime_type: str | None = None) -> IngestionResult:
		"""
		Ingest a file (text, image, audio, or video) and extract text content.
		"""
		print(f"[DEBUG] Ingesting file: {source_path}")
		if not os.path.exists(source_path):
			raise FileNotFoundError(source_path)
		
		# Determine file type and source type
		file_type, detected_mime = self.multimedia_processor.get_file_type(source_path)
		mime_type = mime_type or detected_mime
		
		# Map file types to SourceType enum
		source_type_map = {
			'image': SourceType.IMAGE,
			'audio': SourceType.AUDIO,
			'video': SourceType.VIDEO,
			'text': SourceType.PLAIN
		}
		source_type = source_type_map.get(file_type, SourceType.PLAIN)
		
		print(f"[DEBUG] File type: {file_type}, Source type: {source_type}")
		
		# Process file to extract text content
		if file_type in ['image', 'audio', 'video']:
			print(f"[DEBUG] Processing multimedia file with Gemini...")
			text_content = self.multimedia_processor.process_file(source_path)
		else:
			# Handle as text file
			print(f"[DEBUG] Reading text file...")
			with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
				text_content = f.read()
		
		print(f"[DEBUG] Extracted text content length: {len(text_content)}")
		
		# Create document
		doc = Document(
			id=str(uuid.uuid4()),
			source_type=source_type,
			source_path=source_path,
			metadata={"mime_type": mime_type, "file_type": file_type},
			text_content=text_content,
		)
		
		# Chunk the text content
		chunks = self.chunker.chunk(doc)
		print(f"[DEBUG] Created {len(chunks)} chunks")
		
		# Generate embeddings and store
		embs = self.embedder.embed([c.text for c in chunks])
		self.vector_store.upsert([c.id for c in chunks], embs, chunks)
		
		# Create and store ingestion result
		result = IngestionResult(document=doc, chunks=chunks, num_chunks=len(chunks))
		self.metadata.write_ingestion(result)
		
		print(f"[DEBUG] Ingestion complete. Document ID: {doc.id}")
		return result

	def query(self, request: QueryRequest) -> QueryResponse:
		print(f"[DEBUG] Pipeline.query called with: {request.query[:50]}...")
		pairs: List[Tuple[Chunk, float]] = self.retriever.retrieve(request)
		print(f"[DEBUG] Retrieved {len(pairs)} chunks")
		context = "\n\n".join(c.text for c, _ in pairs)
		prompt = f"Answer the user using the context below. If unsure, say you don't know.\n\nContext:\n{context}\n\nQuestion: {request.query}\nAnswer:"
		print(f"[DEBUG] Calling LLM.generate (LLM type: {type(self.llm).__name__})")
		answer = self.llm.generate(prompt)
		print(f"[DEBUG] LLM returned answer (length: {len(answer)})")
		retrieved = [RetrievedChunk(chunk=c, score=s) for c, s in pairs]
		docs = []
		return QueryResponse(answer=answer, retrieved=retrieved, source_documents=docs, llm_metadata={})
