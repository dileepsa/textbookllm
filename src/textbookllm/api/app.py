"""FastAPI application for TextbookLLM."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..models import QueryRequest, QueryResponse, Document
from ..services.pipeline import DefaultPipeline

# Load .env file from project root
_env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(_env_path)


app = FastAPI(title="TextbookLLM API", version="0.1.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

_pipeline = DefaultPipeline()


class IngestResponse(BaseModel):
	"""Response model for ingestion endpoint."""

	document_id: str
	num_chunks: int


@app.get("/status")
def status() -> dict:
	"""Health check endpoint.
	
	Returns:
		Status dictionary with "ok" key.
	"""
	return {"ok": True}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)) -> IngestResponse:
	"""Ingest a document file.
	
	Args:
		file: Uploaded file to process.
		
	Returns:
		Ingestion result with document ID and chunk count.
	"""
	contents = await file.read()
	tmp_dir = os.path.join("/tmp", "textbookllm")
	os.makedirs(tmp_dir, exist_ok=True)
	local_path = os.path.join(tmp_dir, file.filename or "uploaded_file")
	
	with open(local_path, "wb") as f:
		f.write(contents)
	
	result = _pipeline.ingest(local_path, mime_type=file.content_type)
	return IngestResponse(document_id=result.document.id, num_chunks=result.num_chunks)


@app.post("/query", response_model=QueryResponse)
async def query(q: str = Form(...), k: int = Form(5)) -> QueryResponse:
	"""Query the knowledge base.
	
	Args:
		q: Query question.
		k: Maximum number of chunks to retrieve.
		
	Returns:
		Query response with answer and retrieved chunks.
	"""
	request = QueryRequest(query=q, max_results=k)
	return _pipeline.query(request)


@app.post("/query-filtered", response_model=QueryResponse)
async def query_filtered(
	q: str = Form(...), 
	k: int = Form(5),
	filenames: Optional[str] = Form(None),  # Comma-separated filenames
	document_ids: Optional[str] = Form(None)  # Comma-separated document IDs
) -> QueryResponse:
	"""Query with optional filtering by filenames or document IDs.
	
	Args:
		q: Query question.
		k: Maximum number of chunks to retrieve.
		filenames: Optional comma-separated filenames to filter.
		document_ids: Optional comma-separated document IDs to filter.
		
	Returns:
		Query response with answer and retrieved chunks.
	"""
	filename_list = [f.strip() for f in filenames.split(",")] if filenames else None
	doc_id_list = [d.strip() for d in document_ids.split(",")] if document_ids else None
	
	request = QueryRequest(
		query=q, 
		max_results=k,
		filenames=filename_list,
		document_ids=doc_id_list
	)
	return _pipeline.query(request)


@app.get("/documents", response_model=List[Document])
async def list_documents() -> List[Document]:
	"""List all ingested documents.
	
	Returns:
		List of all documents.
	"""
	return _pipeline.metadata.list_all_documents()


class DocumentInfo(BaseModel):
	id: str
	filename: Optional[str]
	source_type: str
	num_chunks: int = 0


@app.get("/documents/summary", response_model=List[DocumentInfo])
async def list_documents_summary() -> List[DocumentInfo]:
	"""List all documents with summary information.
	
	Returns:
		List of document info summaries.
	"""
	docs = _pipeline.metadata.list_all_documents()
	return [
		DocumentInfo(
			id=doc.id,
			filename=doc.filename,
			source_type=doc.source_type.value,
			num_chunks=0  # Could be calculated if needed
		)
		for doc in docs
	]


class DeleteResponse(BaseModel):
	"""Response model for delete operations."""
	
	success: bool
	message: str


@app.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str) -> DeleteResponse:
	"""Delete a document and its associated chunks.
	
	Args:
		document_id: ID of the document to delete.
		
	Returns:
		Delete response with success status and message.
	"""
	try:
		success = _pipeline.delete_document(document_id)
		if success:
			return DeleteResponse(success=True, message=f"Document {document_id} deleted successfully")
		else:
			return DeleteResponse(success=False, message=f"Document {document_id} not found")
	except Exception as e:
		return DeleteResponse(success=False, message=f"Error deleting document: {str(e)}")


@app.get("/")
def root() -> dict:
	"""Root endpoint.
	
	Returns:
		Service information.
	"""
	return {"service": "textbookllm", "version": "0.1.0"}
