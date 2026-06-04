# Research RAG Engine — Index

> **Senior AI Systems Engineer Design Document**
> Stack: Qdrant · BGE-M3 · BGE-Reranker-v2-m3 · LangChain · FastAPI
> Version: 1.0.0 | Status: Approved for Implementation
> Phase: 4 — RAG Engine Module

---

## Document Index

| # | Document | Description |
|---|---|---|
| 01 | [Retrieval Architecture](./01_retrieval_architecture.md) | BGE-M3 tri-representation design, Qdrant collection schema, hybrid RRF fusion, source ranking algorithm |
| 02 | [Indexing Pipeline](./02_indexing_pipeline.md) | PDF upload, multi-layer parsing, metadata extraction, hierarchical chunking, embedding generation, Qdrant upsert |
| 03 | [Search Pipeline](./03_search_pipeline.md) | Query analysis, encoding, hybrid retrieval, BGE-Reranker cross-encoding, citation generation, search API specs |
| 04 | [Data Flow Diagrams](./04_data_flow_diagrams.md) | 9 Mermaid diagrams covering complete system, indexing, search, agent integration, scoring, citation, LangChain wiring |

---

## System Design Summary

### Core Technology Choices

| Technology | Role | Why |
|---|---|---|
| **BGE-M3** | Document + query encoder | Single model → dense + sparse vectors in one pass; BEIR SOTA; 8192 token context |
| **BGE-Reranker-v2-m3** | Cross-encoder re-ranking | Sees query + chunk together; 30-50% NDCG improvement over bi-encoder alone |
| **Qdrant** | Vector database | Native hybrid (dense + sparse) search; payload filtering before ANN; horizontal sharding |
| **LangChain** | RAG orchestration | StandardRetriever protocol; EnsembleRetriever for hybrid; CompressionRetriever for reranker wrapping |
| **FastAPI** | Async API layer | Matches async Qdrant + async embedding clients; WebSocket for indexing progress |

---

## Feature Coverage Map

| Feature | Implementation | Document |
|---|---|---|
| **PDF Upload** | Multipart → S3 → async Celery task | 02 · Step 1 |
| **Research Paper Parsing** | PDFPlumber → PyMuPDF → Tesseract (layered fallback) | 02 · Step 3 |
| **Chunking Strategy** | 4-tier hierarchical: summary → section → paragraph → sentence | 02 · Step 7 |
| **Embedding Generation** | BGE-M3 (dense 1024-dim + sparse SPLADE) batch=32 | 02 · Step 9 |
| **Semantic Search** | Dense ANN via HNSW (Qdrant) | 03 · Stage 3 |
| **Metadata Search** | Qdrant payload filter + PostgreSQL structured query | 03 · Metadata API |
| **Citation Generation** | APA 7th, IEEE, MLA 9th, BibTeX, inline from chunk payload | 03 · Stage 5 |
| **Source Ranking** | 5-signal composite: reranker + rrf + quality + recency + citations | 01 · Source Ranking |
| **Hybrid Retrieval** | Dense + sparse parallel search → RRF fusion → cross-encoder rerank | 01 · Component 4 |

---

## Qdrant Collections

```
org_{id}_research_chunks   ← Primary retrieval collection
  Vectors: dense(1024) + sparse(SPLADE)
  Payload: chunk_id, doc_id, section, chunk_type, page_range, citations...

org_{id}_research_docs     ← Document-level retrieval
  Vectors: dense(1024) doc summary embedding
  Payload: title, authors, year, doi, journal, citation_count...

org_{id}_claims            ← Verified claims (from Verification Agent)
  Vectors: dense(1024)
  Payload: claim_id, status, confidence, source_doc_ids...
```

---

## Search Latency Budget

| Stage | Time | Cumulative |
|---|---|---|
| Query analysis + expansion | 10ms | 10ms |
| BGE-M3 query encoding (cache miss) | 25ms | 35ms |
| Qdrant hybrid search (50M vectors) | 30ms | 65ms |
| RRF fusion (in-memory) | 2ms | 67ms |
| BGE-Reranker (50 pairs, GPU) | 75ms | 142ms |
| Result assembly + citation gen | 5ms | 147ms |
| **Total (P50)** | | **~150ms** |
| **Total (P95, cache miss)** | | **~450ms** |

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Context header injection** | Prepending doc title + section to each chunk before embedding improves retrieval by 20-30% (proven by Anthropic contextual retrieval research) |
| **Layered PDF parser fallback** | PDFPlumber → PyMuPDF → Tesseract ensures >99% parse success rate across all PDF types |
| **Idempotent indexing (SHA-256 dedup)** | Re-uploading the same paper is safe — no duplicate vectors created |
| **Section-specific chunking** | Tables and equations are atomic chunks — never split across boundaries |
| **Metadata pre-filter in Qdrant** | Filter applied before ANN search, not after — preserves top-K recall |
| **BGE-Reranker threshold 0.3** | Discard below-threshold chunks before composite scoring — prevents low-quality sources reaching LLM context |
| **10-min search result cache** | Research sessions are repetitive — same query from multiple agents → one Qdrant call |
| **RRF k=60** | Standard constant — proven optimal across many retrieval benchmarks |
| **Async indexing (Celery)** | API returns 202 immediately — PDFs up to 100MB can take 30-75 seconds to index |
| **Org-namespaced collections** | `org_{id}_` prefix ensures complete data isolation between organizations in Qdrant |
