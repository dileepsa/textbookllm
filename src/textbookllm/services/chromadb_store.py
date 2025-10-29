# ChromaDB-based Vector and Metadata Store
# Requires: pip install chromadb

from chromadb import Client as ChromaClient
from chromadb.config import Settings
from typing import List, Tuple
import json
from ..models import Chunk, Document, Embedding, IngestionResult
from ..contracts import VectorStore, MetadataStore

class ChromaDBVectorStore(VectorStore):
    def __init__(self, collection_name="vector_store", persist_directory="chroma_db"):
        self.client = ChromaClient(Settings(persist_directory=persist_directory))
        self.collection = self.client.get_or_create_collection(collection_name)

    def _serialize_metadata(self, chunk: Chunk) -> dict:
        """Convert Chunk to ChromaDB-compatible metadata (only simple types)."""
        # Serialize metadata dict, converting enums to strings
        metadata_str = "{}"
        if chunk.metadata:
            # Convert any enum values to their string representation
            serializable_meta = {}
            for key, value in chunk.metadata.items():
                if hasattr(value, 'value'):  # Check if it's an enum
                    serializable_meta[key] = value.value
                else:
                    serializable_meta[key] = value
            metadata_str = json.dumps(serializable_meta)
        
        return {
            "document_id": chunk.document_id,
            "text": chunk.text,
            "order": chunk.order,
            "metadata": metadata_str
        }

    def upsert(self, ids: List[str], embeddings: List[Embedding], metadatas: List[Chunk]) -> None:
        vectors = [emb.vector for emb in embeddings]
        metadatas_dicts = [self._serialize_metadata(c) for c in metadatas]
        self.collection.upsert(ids=ids, embeddings=vectors, metadatas=metadatas_dicts)

    def delete(self, ids: List[str]) -> None:
        """Delete vectors by their IDs."""
        if ids:
            self.collection.delete(ids=ids)

    def search(self, embedding: Embedding, k: int) -> List[Tuple[str, float]]:
        results = self.collection.query(query_embeddings=[embedding.vector], n_results=k)
        ids = results["ids"][0]
        scores = results["distances"][0]
        # Chroma returns L2 distance; convert to similarity (optional)
        similarities = [1 / (1 + d) for d in scores]
        return list(zip(ids, similarities))

class ChromaDBMetadataStore(MetadataStore):
    def __init__(self, collection_name="metadata_store", persist_directory="chroma_db"):
        self.client = ChromaClient(Settings(persist_directory=persist_directory))
        self.collection = self.client.get_or_create_collection(collection_name)
        self._documents = {}
        self._chunks = {}

    def write_ingestion(self, result: IngestionResult) -> None:
        # Store in memory since ChromaDB metadata has type restrictions
        self._documents[result.document.id] = result.document
        for c in result.chunks:
            self._chunks[c.id] = c

    def get_document(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)

    def get_chunks(self, chunk_ids: List[str]) -> List[Chunk]:
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

    def list_all_documents(self) -> List[Document]:
        return list(self._documents.values())

    def get_documents_by_filenames(self, filenames: List[str]) -> List[Document]:
        return [doc for doc in self._documents.values() if doc.filename in filenames]

    def delete_document(self, document_id: str) -> bool:
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
        return [cid for cid, chunk in self._chunks.items() if chunk.document_id == document_id]
