from __future__ import annotations

import hashlib
import os
import uuid
from typing import List, Tuple

from ..contracts import Chunker, Embedder, LLMClient, MetadataStore, Pipeline, Retriever, VectorStore
from ..models import Chunk, Document, Embedding, IngestionResult, QueryRequest, QueryResponse, RetrievedChunk, SourceType


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
	def __init__(self) -> None:
		self.metadata = InMemoryMetadataStore()
		self.chunker = SimpleChunker()
		self.embedder = HashEmbedder()
		self.vector_store = InMemoryVectorStore()
		self.retriever = SimpleRetriever(self.vector_store, self.embedder, self.metadata)
		self.llm = EchoLLM()

	def ingest(self, source_path: str, *, mime_type: str | None = None) -> IngestionResult:
		# Minimal ingestion: read text files; other types are placeholders
		text: str
		if not os.path.exists(source_path):
			raise FileNotFoundError(source_path)
		with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
			text = f.read()
		doc = Document(
			id=str(uuid.uuid4()),
			source_type=SourceType.PLAIN,
			source_path=source_path,
			metadata={},
			text_content=text,
		)
		chunks = self.chunker.chunk(doc)
		embs = self.embedder.embed([c.text for c in chunks])
		self.vector_store.upsert([c.id for c in chunks], embs, chunks)
		result = IngestionResult(document=doc, chunks=chunks, num_chunks=len(chunks))
		self.metadata.write_ingestion(result)
		return result

	def query(self, request: QueryRequest) -> QueryResponse:
		pairs: List[Tuple[Chunk, float]] = self.retriever.retrieve(request)
		context = "\n\n".join(c.text for c, _ in pairs)
		prompt = f"Answer the user using the context below. If unsure, say you don't know.\n\nContext:\n{context}\n\nQuestion: {request.query}\nAnswer:"
		answer = self.llm.generate(prompt)
		retrieved = [RetrievedChunk(chunk=c, score=s) for c, s in pairs]
		docs = []
		return QueryResponse(answer=answer, retrieved=retrieved, source_documents=docs, llm_metadata={})
