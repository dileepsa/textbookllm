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
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


app = FastAPI(title="TextbookLLM API", version="0.1.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Check if BASE64 mode is enabled via environment variable
use_base64_mode = os.getenv("USE_BASE64_MULTIMEDIA", "false").lower() == "true"
print(f"[DEBUG] BASE64 multimedia mode: {'enabled' if use_base64_mode else 'disabled'}")

_pipeline = DefaultPipeline(use_base64_multimedia=use_base64_mode)


class IngestResponse(BaseModel):
	document_id: str
	num_chunks: int


@app.get("/status")
def status() -> dict:
	return {"ok": True}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)):
	# Save to tmp then run pipeline.ingest
	contents = await file.read()
	tmp_dir = os.path.join("/tmp", "textbookllm")
	os.makedirs(tmp_dir, exist_ok=True)
	
	# Sanitize filename to avoid issues with spaces and special characters
	import re
	import uuid
	safe_filename = re.sub(r'[^\w\-_.]', '_', file.filename or 'upload')
	# Add UUID to ensure uniqueness
	name_parts = safe_filename.rsplit('.', 1)
	if len(name_parts) == 2:
		safe_filename = f"{name_parts[0]}_{str(uuid.uuid4())[:8]}.{name_parts[1]}"
	else:
		safe_filename = f"{safe_filename}_{str(uuid.uuid4())[:8]}"
	
	local_path = os.path.join(tmp_dir, safe_filename)
	with open(local_path, "wb") as f:
		f.write(contents)
	result = _pipeline.ingest(local_path, mime_type=file.content_type)
	return IngestResponse(document_id=result.document.id, num_chunks=result.num_chunks)


@app.post("/query", response_model=QueryResponse)
async def query(q: str = Form(...), k: int = Form(5)) -> QueryResponse:
	request = QueryRequest(query=q, max_results=k)
	return _pipeline.query(request)


# Optional root for quick check
@app.get("/")
def root() -> dict:
	return {"service": "textbookllm", "version": "0.1.0"}
