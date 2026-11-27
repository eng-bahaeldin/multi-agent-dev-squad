# AI Prompt & Audit Log

## Step 2 Initial Generation Prompt
You are a Principal AI Systems Architect. Write a production-grade, modular Python 3.11+ Two-Stage RAG Pipeline with fallback to web search, using the official Google GenAI SDK (`google-genai`) for LLM interactions.

Architecture & Requirements:
1. Data Models (`src/schemas.py`):
  - `RetrievedChunk`: `chunk_id` (str), `content` (str), `score` (float), `source` (Literal["internal_doc", "web"]), `metadata` (dict).
  - `RAGResponse`: `answer` (str), `citations` (List[str]), `route_taken` (Literal["INTERNAL_RAG", "WEB_FALLBACK"]), `confidence_score` (float), `transformed_query` (str).
2. Pipeline Modules:
  - Query Rewriter (`src/rewriter.py`): Uses Gemini (`gemini-2.0-flash`) to rewrite conversational follow-ups into standalone queries.
  - Stage 1 Retriever (`src/retriever.py`): Indexes Markdown documents in ChromaDB using `all-MiniLM-L6-v2`, retrieving top K1=20 candidates with hash deduplication.
  - Stage 2 Re-Ranker (`src/reranker.py`): Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` to score candidates, applies sigmoid to raw logits, and gates routing at threshold 0.55.
  - Web Fallback (`src/web_fallback.py`): Uses DuckDuckGo Search when confidence < 0.55, returning the top 3 snippets as `RetrievedChunk` objects.
  - Generator (`src/generator.py`): Uses Gemini to produce grounded answers citing sources as bracketed references (`[1]`, `[2]`), isolating context within boundary tags.
