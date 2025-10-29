from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceType(str, Enum):
	TEXT = "text"
	PDF = "pdf"
	DOCX = "docx"
	PPTX = "pptx"
	MARKDOWN = "md"
	PLAIN = "txt"
	IMAGE = "image"
	AUDIO = "audio"
	VIDEO = "video"
	YOUTUBE = "youtube"


class Document(BaseModel):
	id: str
	source_type: SourceType
	source_path: Optional[str] = None
	metadata: Dict[str, Any] = Field(default_factory=dict)
	text_content: Optional[str] = None
	# Future: binary payloads, extracted frames, transcripts


class Chunk(BaseModel):
	id: str
	document_id: str
	text: str
	order: int
	metadata: Dict[str, Any] = Field(default_factory=dict)


class Embedding(BaseModel):
	vector: List[float]
	dimension: int


class IngestionResult(BaseModel):
	document: Document
	chunks: List[Chunk]
	num_chunks: int


class QueryRequest(BaseModel):
	query: str
	max_results: int = 5


class RetrievedChunk(BaseModel):
	chunk: Chunk
	score: float


class QueryResponse(BaseModel):
	answer: str
	retrieved: List[RetrievedChunk] = Field(default_factory=list)
	source_documents: List[Document] = Field(default_factory=list)
	llm_metadata: Dict[str, Any] = Field(default_factory=dict)
