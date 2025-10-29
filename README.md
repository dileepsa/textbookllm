# Multimodal Data Processing System (Notebook LLM Clone)

A modular Python system to ingest multimodal files (text, image, audio/video), build a knowledge base, and answer natural language queries using Gemini (free) or a pluggable LLM.

## Tech Stack
- Backend: Python (FastAPI)
- UI: Static HTML/CSS/JS (optional; included)
- Models: Pydantic v2

## High-level Architecture
- Contracts: Clear ABC interfaces for loaders, parsers, chunkers, embedders, vector and metadata stores, retriever, LLM, and pipeline.
- Services: Pluggable implementations living under `textbookllm/services/*`.
- API: `FastAPI` endpoints for ingest and query.
- UI: Minimal static page for upload and querying the knowledge base.

## Key Contracts (see `textbookllm/contracts.py`)
- FileLoader → loads file bytes/metadata
- DocumentParser → extracts text/frames/tracks from files
- Chunker → splits extracted content into chunks
- Embedder → converts chunks to vector embeddings
- VectorStore → upserts and searches embeddings
- MetadataStore → stores/retrieves documents and chunk metadata
- Retriever → retrieves candidate chunks for a query
- LLMClient → generates responses from retrieved context
- Pipeline → orchestrates ingestion and query flow

## Repository Layout
```
src/textbookllm/
  __init__.py
  contracts.py
  models.py
  api/
    app.py        # FastAPI app
  services/
    pipeline.py   # Default in-memory pipeline
    gemini.py     # Gemini LLM client
ui/
  index.html
  styles.css
  app.js
```

## Running Locally
1. Install dependencies (Poetry recommended):
```bash
poetry install
poetry run uvicorn textbookllm.api.app:app --reload
```

2. Open the UI:
- Serve `ui/` directory with a simple server:
```bash
cd ui
python -m http.server 8080
```
- Visit `http://127.0.0.1:8080` with API at `http://127.0.0.1:8000`.

## Gemini setup (optional but recommended)
1. Get an API key from [Google AI Studio](https://aistudio.google.com/apikey)
2. Edit the `.env` file in the project root and add your API key:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```
3. The `DefaultPipeline` will automatically use Gemini when `GEMINI_API_KEY` is present; otherwise it falls back to a simple echo model for development.

## Contribution Guide
- Choose a component and implement the interface in `contracts.py`.
- Place your implementation under an appropriate module inside `textbookllm/services/`.
- Add tests where reasonable.
- Wire your component into a composed pipeline (e.g., extend `DefaultPipeline` or create a new one) and update the API wiring if needed.

### Parallel Work Streams
- Parsers: PDF, DOCX, PPTX, Markdown, TXT, Image frames, Audio transcripts, YouTube transcripts
- Embedders: Gemini embeddings (if available), sentence-transformers, OpenAI (optional)
- Vector Stores: FAISS, PGVector, Chroma, Elasticsearch, Pinecone (adapters)
- Metadata Stores: SQLite, Postgres
- Retriever: BM25 + dense hybrid, Maximal Marginal Relevance
- Reranker: Cross-encoder rerankers (optional)
- LLMs: Gemini client, mock client for dev
- UI: Streamlit alt UI, better HTML page, file drag-and-drop

## Notes
- Current default pipeline ingests plain text files only, with a hash-based fake embedder and in-memory stores for quick iteration.
- Replace components incrementally without changing the API surface.
