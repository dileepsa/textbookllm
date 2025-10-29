"""FastAPI application for TextbookLLM."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..models import QueryRequest, QueryResponse
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


@app.get("/")
def root() -> dict:
	"""Root endpoint.
	
	Returns:
		Service information.
	"""
	return {"service": "textbookllm", "version": "0.1.0"}
