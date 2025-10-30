"""Simple retriever implementation."""
from __future__ import annotations

from typing import List, Tuple

from ..contracts import Retriever, VectorStore, MetadataStore, Embedder
from ..models import QueryRequest, Chunk


class SimpleRetriever(Retriever):
	"""Simple retriever using vector search with filtering support."""
	
	def __init__(self, vector_store: VectorStore, embedder: Embedder, metadata: MetadataStore) -> None:
		self._vs = vector_store
		self._embed = embedder
		self._meta = metadata

	def retrieve(self, request: QueryRequest) -> List[Tuple[Chunk, float]]:
		"""Retrieve relevant chunks for a query with optional filtering."""
		[q_emb] = self._embed.embed([request.query])
		
		# Get more results initially for filtering
		search_k = request.max_results * 10 if (request.document_ids or request.filenames) else request.max_results
		hits = self._vs.search(q_emb, search_k)
		chunks = self._meta.get_chunks([cid for cid, _ in hits])
		score_map = {cid: score for cid, score in hits}
		
		# Apply filtering if document_ids or filenames are specified
		filtered_chunks = []
		if request.document_ids:
			# Filter by document IDs
			allowed_doc_ids = set(request.document_ids)
			filtered_chunks = [(c, score_map.get(c.id, 0.0)) for c in chunks if c.document_id in allowed_doc_ids]
		elif request.filenames:
			# Filter by filenames - need to get documents to check filenames
			target_docs = self._meta.get_documents_by_filenames(request.filenames)
			allowed_doc_ids = {doc.id for doc in target_docs}
			filtered_chunks = [(c, score_map.get(c.id, 0.0)) for c in chunks if c.document_id in allowed_doc_ids]
		else:
			# No filtering, return all
			filtered_chunks = [(c, score_map.get(c.id, 0.0)) for c in chunks]
		
		# Return top max_results after filtering
		filtered_chunks.sort(key=lambda x: x[1], reverse=True)
		return filtered_chunks[:request.max_results]

