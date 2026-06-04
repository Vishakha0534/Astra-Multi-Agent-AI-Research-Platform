# Research RAG Engine — Data Flow Diagrams

## Diagram 1 — Complete System Data Flow

End-to-end view of all data paths from document upload to agent consumption:

```mermaid
flowchart TB
    subgraph CLIENTS["Clients"]
        UI["Next.js 15 Frontend\nDrag-drop PDF upload\nSearch interface\nCitation panel"]
        AGENT["Research Agent\n(Gemini 2.5 Pro)\nLangChain retriever"]
        LIT_AGENT["Literature Agent\n(Claude Sonnet)\nLangChain retriever"]
    end

    subgraph GATEWAY["API Gateway"]
        FASTAPI["FastAPI\nUpload endpoint\nSearch endpoint\nCitation endpoint\nStatus endpoint"]
    end

    subgraph STORAGE["Primary Storage"]
        S3["AWS S3 / MinIO\nRaw PDF storage\nImmutable originals\nOrg-namespaced keys"]
        PG["PostgreSQL\ndocuments table\ndocument_chunks table\nsource_rankings table"]
    end

    subgraph QUEUE["Async Processing"]
        REDIS_Q["Redis Task Queue\nCelery broker\nPriority lanes: high/normal/batch"]
        WORKERS["Celery Workers\n(4 per node)\nIndexing pipeline execution"]
    end

    subgraph ML["ML Processing"]
        PARSER["Document Parser\nPDFPlumber + PyMuPDF\n+ Tesseract OCR"]
        META_API["Metadata APIs\nCrossRef + ArXiv\n+ Semantic Scholar"]
        BGE_M3["BGE-M3 Encoder\nFlagEmbedding\ndense + sparse\nin one pass"]
        RERANKER["BGE-Reranker-v2-m3\nCross-encoder\nTop-50 → Top-K"]
    end

    subgraph VECTOR_DB["Vector Database"]
        QDRANT["Qdrant Cluster\norg_{id}_research_chunks\norg_{id}_research_docs\norg_{id}_claims"]
    end

    subgraph CACHE["Caching Layer"]
        REDIS_C["Redis Cache\nSearch result cache\nEmbedding cache\nDocument status"]
    end

    %% Upload Path
    UI -->|"POST /upload\nmultipart/form-data"| FASTAPI
    FASTAPI -->|"S3 PUT\nOriginal PDF"| S3
    FASTAPI -->|"Enqueue task"| REDIS_Q
    FASTAPI -->|"INSERT document row\nstatus=pending"| PG

    %% Processing Path
    REDIS_Q --> WORKERS
    WORKERS -->|"GET s3_key"| S3
    WORKERS --> PARSER
    WORKERS --> META_API
    WORKERS --> BGE_M3
    WORKERS -->|"Upsert points\nwait=True"| QDRANT
    WORKERS -->|"UPDATE status=indexed\nINSERT chunks"| PG
    WORKERS -->|"Publish\ndocument_indexed event"| REDIS_C

    %% Search Path
    AGENT -->|"POST /search/semantic\n{query, job_id, filters}"| FASTAPI
    LIT_AGENT -->|"POST /search/semantic"| FASTAPI
    UI -->|"POST /search/hybrid"| FASTAPI

    FASTAPI -->|"Cache check"| REDIS_C
    REDIS_C -->|"Cache miss"| FASTAPI
    FASTAPI -->|"BGE-M3 query encode"| BGE_M3
    FASTAPI -->|"Hybrid ANN + sparse search\nwith payload filter"| QDRANT
    QDRANT -->|"Top-50 candidates"| FASTAPI
    FASTAPI -->|"50 pairs for scoring"| RERANKER
    RERANKER -->|"Re-ranked scores"| FASTAPI
    FASTAPI -->|"Write result to cache\nTTL=10min"| REDIS_C
    FASTAPI -->|"Ranked results\n+ citations\n+ context window"| AGENT
    FASTAPI -->|"Ranked results\n+ citations"| UI
```

---

## Diagram 2 — Indexing Pipeline Data Flow

Detailed data transformations from raw PDF to indexed vectors:

```mermaid
flowchart TD
    RAW_PDF["Raw PDF Binary\n(file bytes)"] 

    RAW_PDF --> HASH["SHA-256 Hash\ncontent deduplication"]

    HASH -->|new| PARSE_LAYER

    subgraph PARSE_LAYER["Parsing Layer"]
        direction LR
        PDF_P["PDFPlumber\ntext + layout + tables"]
        PDF_M["PyMuPDF\n(fallback)"]
        OCR["Tesseract OCR\n(scanned PDF fallback)"]
        PDF_P --> SELECTOR{quality >= 0.85?}
        SELECTOR -->|no| PDF_M --> SELECTOR2{quality >= 0.70?}
        SELECTOR2 -->|no| OCR
    end

    PARSE_LAYER --> PARSED_DOC

    PARSED_DOC["Parsed Document\n{text, pages, blocks, tables}\nas dict"]

    PARSED_DOC --> META_EXTRACT

    subgraph META_EXTRACT["Metadata Extraction"]
        direction LR
        DOI_REGEX["DOI Regex\nfrom PDF text"]
        CROSS_API["CrossRef API\nif DOI found"]
        ARXIV_API["ArXiv API\nif arXiv ID found"]
        S2_API["Semantic Scholar\nfuzzy title lookup"]
        DOI_REGEX --> CROSS_API
        DOI_REGEX --> ARXIV_API
        PARSED_DOC --> S2_API
    end

    META_EXTRACT --> VALIDATED_META["Validated Metadata\n{title, authors, year, doi,\njournal, abstract, keywords,\ncitation_count}"]

    PARSED_DOC --> CLEAN

    subgraph CLEAN["Cleaning & Classification"]
        direction LR
        NORM["Text Normalization\nligatures, hyphenation, unicode"]
        SECTION["Section Classifier\nrule-based + SciBERT\n(abstract, methodology, etc.)"]
        NORM --> SECTION
    end

    CLEAN --> CLEAN_LABELED["Cleaned + Section-Labeled\nDocument Blocks"]

    CLEAN_LABELED --> CHUNK_ENGINE

    subgraph CHUNK_ENGINE["Chunking Engine"]
        T0["Tier 0: Doc summary\n512 tokens\nfor doc-level index"]
        T1["Tier 1: Sections\nmax 2000 tokens\nno overlap"]
        T2["Tier 2: Paragraphs\n384-512 tokens\n64 token overlap\n(primary retrieval)"]
        T3["Tier 3: Sentences\n64-128 tokens\nfor fine-grained"]
        SP["Special: Tables\nEquations\nFigure captions"]
    end

    CHUNK_ENGINE --> RAW_CHUNKS["Raw Chunks List\n~30-200 chunks\nper document"]

    RAW_CHUNKS --> ENRICH["Chunk Enrichment\nInject context header\nAttach full metadata\nBuild citation payloads\nGenerate chunk_id"]

    VALIDATED_META --> ENRICH

    ENRICH --> ENRICHED_CHUNKS["Enriched Chunks\n{text_with_header, text_clean,\nchunk_id, section, page_range,\ncitation (APA/IEEE/MLA),\ndoc_metadata}"]

    ENRICHED_CHUNKS --> BGE_ENCODE

    subgraph BGE_ENCODE["BGE-M3 Encoding"]
        BATCH["Batch=32\nchunks"]
        BGE["BGE-M3\nForward Pass"]
        DENSE_V["Dense Vectors\n[N × 1024] float32\nL2-normalized"]
        SPARSE_V["Sparse Vectors\n[N × vocab] SPLADE\ntop-128 active dims"]
        BATCH --> BGE --> DENSE_V & SPARSE_V
    end

    DENSE_V & SPARSE_V & ENRICHED_CHUNKS --> POINT_BUILD

    POINT_BUILD["Build PointStruct\n{id: UUID(chunk_id),\nvectors: {dense: [...], sparse: {...}},\npayload: {doc_id, org_id, section,\nchunk_type, page_range, citations...}}"]

    POINT_BUILD --> QDRANT_UPSERT

    subgraph QDRANT_UPSERT["Qdrant Upsert (atomic)"]
        BATCH_32["Batch of 32 PointStructs"]
        UPSERT["collection.upsert(\n  points=batch,\n  wait=True\n)"]
        ACK["200 OK — all indexed"]
        BATCH_32 --> UPSERT --> ACK
    end

    POINT_BUILD --> DOC_COLLECTION["Also upsert document-level\nsummary vector to\nresearch_docs collection"]

    QDRANT_UPSERT --> PG_WRITE

    PG_WRITE["PostgreSQL Write\nUPDATE documents SET\nstatus=indexed, chunk_count=N\nINSERT document_chunks\n(chunk_id, qdrant_point_id, metadata)"]

    PG_WRITE --> DONE["✅ Document Indexed\nWebSocket notification\nStatus: indexed"]
```

---

## Diagram 3 — Search Pipeline Data Flow

Query-to-result data transformations:

```mermaid
flowchart TD
    QUERY["User/Agent Query\n'What are recent methodologies\nfor few-shot NLP?'"]

    QUERY --> ANALYZE

    subgraph ANALYZE["Query Analysis"]
        TYPE["Type Classification\nhybrid query"]
        FILTER_EX["Filter Extraction\nyear_min=2021\nsection=[methodology, results]"]
        EXPAND["Query Expansion\n+ synonyms, acronyms\n+ HyDE generation\n(0.7 × query + 0.3 × hyde)"]
        TYPE --> FILTER_EX --> EXPAND
    end

    ANALYZE --> ANALYSIS_OUTPUT["Analysis Output\n{query_type: hybrid,\nalpha_dense: 0.5, alpha_sparse: 0.5,\nfilters: {year>=2021, section:[...]}}\nexpanded_query: '...'"]

    ANALYSIS_OUTPUT --> CACHE_CHECK["Redis Cache Check\nKey: search:{sha256(query+filters)}\nTTL: 10 min"]

    CACHE_CHECK -->|HIT ~5ms| RETURN_CACHED["Return Cached Result\n{ranked chunks + citations}"]

    CACHE_CHECK -->|MISS| ENCODE

    subgraph ENCODE["Query Encoding (BGE-M3)"]
        Q_DENSE["Dense Query Vector\n[1024 float32]"]
        Q_SPARSE["Sparse Query Vector\n{token: weight, ...}"]
    end

    ENCODE --> PARALLEL_SEARCH

    subgraph PARALLEL_SEARCH["Parallel Qdrant Search"]
        direction LR
        D_SEARCH["Dense ANN Search\nHNSW ef=128\nTop-100\nwith payload filter"]
        S_SEARCH["Sparse Index Search\nInverted index\nTop-100\nwith payload filter"]
    end

    PARALLEL_SEARCH --> D_RESULTS["Dense Results\n100 chunks\n{chunk_id, score, payload}"]
    PARALLEL_SEARCH --> S_RESULTS["Sparse Results\n100 chunks\n{chunk_id, score, payload}"]

    D_RESULTS & S_RESULTS --> RRF["RRF Fusion\nk=60\nMerge 100+100 lists\nDeduplicate\nTop-50 by RRF score"]

    RRF --> TOP50["50 Fused Candidates\n{chunk_id, chunk_text,\nrrf_score, section,\npages, doc_metadata}"]

    TOP50 --> RERANK

    subgraph RERANK["BGE-Reranker-v2-m3"]
        PAIRS["50 (query, chunk_text) pairs"]
        CROSS["Cross-encoder\nFull attention\nquery + chunk together"]
        SCORES["50 relevance scores\n[0.0 – 1.0]"]
        PAIRS --> CROSS --> SCORES
    end

    RERANK --> FILTER_LOW["Filter: score < 0.3 → discard"]

    FILTER_LOW --> COMPOSITE["Composite Score\n0.45×reranker\n+ 0.25×rrf\n+ 0.15×source_quality\n+ 0.10×recency\n+ 0.05×citations"]

    COMPOSITE --> TOPK["Top-K Results\n(K = 10 default)\nsorted by composite score"]

    TOPK --> CITE_GEN

    subgraph CITE_GEN["Citation Generation"]
        APA_GEN["APA 7th\n(Vaswani et al., 2017)"]
        IEEE_GEN["IEEE Format\n[1] A. Vaswani et al."]
        INLINE_GEN["Inline Citation\n(Vaswani et al., 2017, p.4)"]
        BIBTEX["BibTeX\n@inproceedings{...}"]
    end

    CITE_GEN --> CONTEXT["Context Window Assembly\n[RETRIEVED CONTEXT]\nSource 1 (0.94)...\nSource 2 (0.87)...\n[INSTRUCTION TO LLM]"]

    TOPK --> CACHE_WRITE["Write to Redis\nTTL: 10 minutes"]

    CONTEXT --> RESPONSE["Search Response\n{results: [...],\ncontext_window: '...',\nlatency_ms: 145,\ntotal_results: 10}"]
```

---

## Diagram 4 — Agent Integration Data Flow

How the Research and Literature agents use the RAG engine:

```mermaid
sequenceDiagram
    participant PLANNER as Planner Agent (GPT-4o)
    participant STATE as ResearchState (Graph)
    participant RES_AGENT as Research Agent (Gemini)
    participant LIT_AGENT as Literature Agent (Claude)
    participant RAG as RAG Engine (FastAPI)
    participant QDRANT as Qdrant
    participant BGE as BGE-M3 + Reranker

    PLANNER->>STATE: Write sub_tasks\n{research_tasks, literature_tasks}

    par Parallel execution
        STATE->>RES_AGENT: sub_tasks[assigned=research_agent]
        and
        STATE->>LIT_AGENT: sub_tasks[assigned=literature_review_agent]
    end

    Note over RES_AGENT: For each sub-task, Research Agent\ndoes BOTH web search AND RAG retrieval

    RES_AGENT->>RAG: POST /search/hybrid\n{query: sub_task.description,\njob_id, filters: {year_min: 2020}}

    RAG->>BGE: Encode query\n(dense + sparse)
    BGE-->>RAG: Query vectors

    RAG->>QDRANT: Hybrid search\n(dense + sparse + payload filter)
    QDRANT-->>RAG: Top-50 candidates

    RAG->>BGE: Rerank 50 pairs
    BGE-->>RAG: Ranked scores

    RAG-->>RES_AGENT: Top-10 chunks\n{text, citations, metadata\ncomposite_score, context_window}

    RES_AGENT->>STATE: Write raw_sources\n{source_id, text, citation, score\ndoc_metadata, chunk_type}

    Note over LIT_AGENT: Literature Agent focuses\non academic paper chunks only

    LIT_AGENT->>RAG: POST /search/semantic\n{query: sub_task.description,\nfilters: {source_type: [arxiv, journal],\nlevel_of_evidence: conference_paper\nsection: [abstract, results]}}

    RAG-->>LIT_AGENT: Top-10 academic chunks\nwith full citation data

    LIT_AGENT->>STATE: Write literature_papers\n{paper_id, doi, authors, year\nabstract_chunk, key_findings\ncitation_apa, citation_ieee}

    Note over STATE: merge_research node\ncombines raw_sources + literature_papers

    STATE->>STATE: merged_corpus ready\nfor Verification Agent
```

---

## Diagram 5 — Multi-Collection Query Fan-Out

When the Insight Agent needs cross-document retrieval:

```mermaid
flowchart TD
    INSIGHT_AGENT["Insight Agent (GPT-4o)\nNeeds: cross-document\npattern synthesis\nfor verified claims"]

    INSIGHT_AGENT --> FAN_OUT["Fan-out to 3 collections\n(parallel Qdrant queries)"]

    FAN_OUT --> Q1["Query: org_{id}_research_chunks\nFilter: job_id=current\nchunk_type=results\nTop-20 methodology chunks"]

    FAN_OUT --> Q2["Query: org_{id}_claims\nFilter: job_id=current\nstatus=VERIFIED\nconfidence >= 0.8\nTop-20 verified claims"]

    FAN_OUT --> Q3["Query: org_{id}_research_docs\nFilter: org_id\nyear >= 2020\ncitation_count >= 100\nTop-5 high-impact docs"]

    Q1 --> MERGE_RESULTS["Merge Results\nAssign collection-specific weights\nchunks: 0.5\nclaims: 0.35\ndocs: 0.15"]
    Q2 --> MERGE_RESULTS
    Q3 --> MERGE_RESULTS

    MERGE_RESULTS --> RERANK_CROSS["BGE-Reranker\nCross-collection re-ranking\nUnified relevance scoring"]

    RERANK_CROSS --> SYNTHESIS_CONTEXT["Synthesis Context\n{verified_claims with sources,\nhigh-impact doc summaries,\ncross-doc pattern evidence}"]

    SYNTHESIS_CONTEXT --> INSIGHT_AGENT
```

---

## Diagram 6 — Hybrid Retrieval Scoring Data Flow

Detailed view of how scores flow through the hybrid retrieval system:

```mermaid
flowchart TD
    subgraph INPUT["Query Input"]
        Q["'transformer attention\nfor sequence modeling'\nalpha_dense=0.5\nalpha_sparse=0.5"]
    end

    subgraph DENSE_LANE["Dense Retrieval Lane"]
        DV["Dense Query Vector\n[1024 float32]"]
        DHNSW["HNSW ANN Search\n(Cosine)"]
        DR["Dense Results\n[(chunk_A, 0.92),\n(chunk_B, 0.88),\n(chunk_C, 0.85),...]"]
        DRANK["Dense Rank List\nchunk_A: rank 1\nchunk_B: rank 2\nchunk_C: rank 3"]
    end

    subgraph SPARSE_LANE["Sparse Retrieval Lane"]
        SV["Sparse Query Vector\n{transformer:0.8,\nattention:0.9,\nsequence:0.6,...}"]
        SINV["Inverted Index Search\n(Dot Product)"]
        SR["Sparse Results\n[(chunk_B, 0.95),\n(chunk_D, 0.82),\n(chunk_A, 0.78),...]"]
        SRANK["Sparse Rank List\nchunk_B: rank 1\nchunk_D: rank 2\nchunk_A: rank 3"]
    end

    Q --> DV --> DHNSW --> DR --> DRANK
    Q --> SV --> SINV --> SR --> SRANK

    DRANK & SRANK --> RRF_CALC

    subgraph RRF_CALC["RRF Fusion (k=60)"]
        FORMULA["chunk_A: 1/(60+1) + 1/(60+3)\n= 0.01639 + 0.01587 = 0.03226\n\nchunk_B: 1/(60+2) + 1/(60+1)\n= 0.01613 + 0.01639 = 0.03252\n\nchunk_C: 1/(60+3) + 0\n= 0.01587 = 0.01587\n\nchunk_D: 0 + 1/(60+2)\n= 0.01613 = 0.01613"]
        FUSED["Fused Ranking\n1. chunk_B: 0.03252\n2. chunk_A: 0.03226\n3. chunk_D: 0.01613\n4. chunk_C: 0.01587"]
    end

    FUSED --> RERANKER_IN

    subgraph RERANKER_IN["BGE-Reranker Cross-Encoder"]
        CE1["(query, chunk_B) → 0.94"]
        CE2["(query, chunk_A) → 0.91"]
        CE3["(query, chunk_D) → 0.72"]
        CE4["(query, chunk_C) → 0.45"]
    end

    RERANKER_IN --> COMPOSITE_CALC

    subgraph COMPOSITE_CALC["Composite Score"]
        CS_B["chunk_B: 0.45×0.94 + 0.25×norm(0.03252) + 0.15×quality + 0.10×recency + 0.05×cite_weight = 0.891"]
        CS_A["chunk_A: 0.45×0.91 + ... = 0.864"]
        CS_D["chunk_D: 0.45×0.72 + ... = 0.693"]
        CS_C["chunk_C: 0.45×0.45 + ... = 0.441 → filtered (< 0.5)"]
    end

    COMPOSITE_CALC --> FINAL_RANK["Final Ranking\n1. chunk_B (0.891)\n2. chunk_A (0.864)\n3. chunk_D (0.693)"]
```

---

## Diagram 7 — Citation Generation Data Flow

```mermaid
flowchart LR
    CHUNK_PAYLOAD["Chunk Payload\n(from Qdrant)"]

    CHUNK_PAYLOAD --> META["Doc Metadata\n{title, authors[], year,\ndoi, journal, volume,\npages, arxiv_id}"]

    CHUNK_PAYLOAD --> LOC["Location Info\n{page_range[0],\nsection}"]

    META & LOC --> CITE_ENGINE["Citation Engine\n(rule-based formatter\nper standard)"]

    CITE_ENGINE --> APA["APA 7th Edition\nAuthor, A., & Author, B. (Year).\nTitle. Journal, Volume(Issue),\nPages. https://doi.org/..."]

    CITE_ENGINE --> IEEE["IEEE Format\n[N] A. Author, B. Author,\n'Title,' in Journal,\nvol. X, no. Y, pp. ZZ-ZZ,\nYear, doi: ..."]

    CITE_ENGINE --> MLA["MLA 9th Edition\nAuthor, First, and Second Author.\n'Title.' Journal,\nvol. X, Year, pp. ZZ-ZZ."]

    CITE_ENGINE --> BIBTEX["BibTeX\n@article{author2017title,\n  author={Author, A.},\n  title={Title},\n  journal={Journal},\n  year={2017},\n  doi={...}\n}"]

    CITE_ENGINE --> INLINE["In-text Citation\n(Author et al., Year, p. N)"]

    CITE_ENGINE --> HYPERLINK["DOI Hyperlink\nhttps://doi.org/{doi}"]
```

---

## Diagram 8 — LangChain Retriever Integration

How LangChain wraps the RAG engine for agent consumption:

```mermaid
flowchart TD
    subgraph LC_INTEGRATION["LangChain Integration"]

        subgraph RETRIEVER["QdrantHybridSearchRetriever"]
            EMB["BGE-M3EmbeddingWrapper\n(FlagEmbedding → LangChain format)"]
            QDRANT_VS["Qdrant VectorStore\nClient(host, api_key)\ncollection=org_{id}_chunks"]
            HYBRIDGE["Hybrid Bridge\ndense_search + sparse_search\n+ RRF fusion (built-in)"]
        end

        subgraph RERANK_WRAPPER["BGERerankerWrapper"]
            RANKER["BGEReranker(model=bge-reranker-v2-m3)\nCompressionRetriever wraps\nbase retriever"]
        end

        subgraph META_RET["MetadataRetriever"]
            PG_QUERY["PostgreSQL query\nfor metadata-only searches"]
        end

        subgraph ENSEMBLE["EnsembleRetriever"]
            COMBO["Combine:\n- QdrantHybridSearchRetriever\n- MetadataRetriever\nweights=[0.8, 0.2]"]
        end

        subgraph CHAIN["RAG Chain"]
            HISTORY["ConversationBufferMemory\nchat history for\nmulti-turn sessions"]
            QA["ConversationalRetrievalChain\n+ custom prompt template\nwith citation instructions"]
        end

        RETRIEVER --> RERANK_WRAPPER
        META_RET --> ENSEMBLE
        RERANK_WRAPPER --> ENSEMBLE
        ENSEMBLE --> CHAIN
    end

    AGENT["Research Agent\n(Gemini 2.5 Pro)"] --> CHAIN
    CHAIN -->|"retriever.get_relevant_documents(query)"| ENSEMBLE
    ENSEMBLE -->|"Top-K Documents\n(LangChain Document objects\nwith metadata)"| CHAIN
    CHAIN --> AGENT
```

---

## Diagram 9 — System Capacity & Throughput

```mermaid
flowchart LR
    subgraph THROUGHPUT["System Throughput (per node)"]
        IDX["Indexing\n~50 docs/hour (GPU)\n~1,200 docs/day\nper Celery worker"]
        SEARCH["Search\n50 concurrent queries\nP95 < 500ms\nwith reranker"]
        EMBED["Embedding\n2,000 chunks/min\n(BGE-M3, GPU, batch=32)"]
        RERANK["Re-ranking\n300 pairs/sec\n(BGE-Reranker, GPU)"]
    end

    subgraph SCALE["Horizontal Scaling"]
        H_IDX["Indexing Workers\nScale: add Celery nodes\nStateless — just queue + Qdrant"]
        H_SEARCH["Search Nodes\nScale: add API nodes\nLoad balanced (Nginx/Traefik)"]
        H_QDRANT["Qdrant Cluster\nScale: add shards\nReplication factor: 2"]
        H_EMBED["Embedding Service\nScale: multiple GPU workers\nBehind gRPC load balancer"]
    end

    subgraph LIMITS["System Limits (single node)"]
        MAX_DOCS["Max indexed docs: ~1M\n(50 chunks each = 50M points)"]
        MAX_COL["Qdrant: 50M vectors @ 1024-dim\n~200GB with int8 quantization"]
        MAX_CONC["Max concurrent searches: 100\n(with GPU reranker: 50)"]
    end
```
