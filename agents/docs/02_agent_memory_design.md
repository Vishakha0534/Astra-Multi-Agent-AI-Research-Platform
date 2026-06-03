# Multi-Agent AI Research System — Agent Memory Design

## Memory Architecture Overview

The system employs a **four-tier memory architecture** — each tier optimized for different temporal and access patterns:

```mermaid
flowchart TB
    subgraph T1["Tier 1 — Working Memory (In-Graph State)"]
        direction LR
        GS["ResearchState\n(TypedDict)\nShared across all agents\nLives for one job execution\nIn-memory / Redis-backed"]
    end

    subgraph T2["Tier 2 — Episodic Memory (PostgreSQL)"]
        direction LR
        JOB["Research Jobs Table\nJob-level metadata\nStatus, plan, quality score"]
        SOURCES["Sources Table\nAll gathered sources\nWith full metadata"]
        LOGS["Agent Logs Table\nPer-agent execution records\nTokens, cost, latency"]
    end

    subgraph T3["Tier 3 — Semantic Memory (Qdrant Vector Store)"]
        direction LR
        CHUNKS["Source Content Chunks\nChunk size: 512 tokens\nOverlap: 50 tokens\nEmbedded: text-embedding-3-large"]
        CLAIMS["Verified Claims\nEmbedded for semantic search\nWith confidence scores"]
        LIT["Literature Abstracts\nPaper content chunks\nWith citation metadata"]
    end

    subgraph T4["Tier 4 — Long-Term Memory (PostgreSQL + Redis)"]
        direction LR
        PATTERNS["Research Pattern Cache\nOrg-level successful\nresearch strategies"]
        DOMAIN["Domain Knowledge Base\nCurated facts per domain\nBuilt across jobs"]
        FEEDBACK["Human Feedback Loop\nReport quality scores\nAgent performance metrics"]
    end

    T1 <-->|"Flush on completion"| T2
    T1 <-->|"Write during execution"| T3
    T2 <-->|"Load history"| T4
    T3 <-->|"Retrieve context"| T1
```

---

## Tier 1 — Working Memory (Graph State)

The **central shared state** object that all agents read from and write to. This is the "blackboard" pattern — agents communicate exclusively through state, not direct calls.

### ResearchState Schema

```mermaid
classDiagram
    class ResearchState {
        +job_id: UUID
        +org_id: UUID
        +user_id: UUID
        +user_query: str
        +created_at: datetime
        +current_node: str
        +execution_phase: ExecutionPhase

        +orchestration_plan: dict
        +sub_tasks: list[SubTask]
        +success_criteria: list[str]
        +token_budget: TokenBudget

        +raw_sources: list[SourceEvidence]
        +literature_papers: list[LiteraturePaper]
        +verified_claims: list[VerifiedClaim]
        +contradictions: list[Contradiction]
        +resolved_contradictions: list[Contradiction]

        +key_findings: list[Finding]
        +insights: InsightOutput
        +recommendations: list[Recommendation]
        +final_report: str

        +agent_outputs: dict[AgentName, AgentOutput]
        +agent_errors: dict[AgentName, AgentError]
        +retry_counts: dict[AgentName, int]
        +fallback_activations: list[FallbackRecord]

        +quality_scores: dict[str, float]
        +pipeline_blocked: bool
        +human_review_required: bool
        +total_tokens_used: int
        +total_cost_usd: Decimal
    }

    class TokenBudget {
        +total: int
        +per_agent: dict[str, int]
        +consumed: dict[str, int]
        +remaining: dict[str, int]
    }

    class SubTask {
        +id: str
        +title: str
        +description: str
        +type: TaskType
        +priority: Priority
        +assigned_agent: str
        +status: TaskStatus
        +dependencies: list[str]
        +output: dict|None
    }

    class AgentOutput {
        +agent_name: str
        +node_name: str
        +started_at: datetime
        +completed_at: datetime
        +input_tokens: int
        +output_tokens: int
        +cost_usd: Decimal
        +quality_score: float
        +output_data: dict
        +is_fallback: bool
    }

    ResearchState --> TokenBudget
    ResearchState --> SubTask
    ResearchState --> AgentOutput
```

### State Isolation Per Agent

Each agent reads its **designated slice** of state and writes to its **designated output fields** only. No agent can overwrite another agent's output:

```mermaid
flowchart LR
    STATE[ResearchState]

    PLAN_R["Planner Agent\nREADS: user_query\nWRITES: orchestration_plan\nsub_tasks, success_criteria"]
    RES_R["Research Agent\nREADS: sub_tasks, token_budget\nWRITES: raw_sources\nagent_outputs.research"]
    LIT_R["Literature Agent\nREADS: sub_tasks, token_budget\nWRITES: literature_papers\nagent_outputs.literature"]
    VER_R["Verification Agent\nREADS: raw_sources, literature_papers\nWRITES: verified_claims\nquality_scores.verification"]
    CON_R["Contradiction Agent\nREADS: verified_claims\nWRITES: contradictions\nresolved_contradictions"]
    INS_R["Insight Agent\nREADS: verified_claims, contradictions\nWRITES: key_findings, insights\nrecommendations"]
    REP_R["Report Agent\nREADS: all above\nWRITES: final_report"]

    STATE <--> PLAN_R
    STATE <--> RES_R
    STATE <--> LIT_R
    STATE <--> VER_R
    STATE <--> CON_R
    STATE <--> INS_R
    STATE <--> REP_R
```

### State Persistence Strategy

| Trigger | Action |
|---|---|
| After each agent node completes | Snapshot state to Redis (TTL = 2 hours) |
| After each checkpoint | Serialize full state to PostgreSQL `research_jobs.state_checkpoint` (JSONB) |
| On pipeline failure | Persist final state + error context to DB for debugging |
| On pipeline completion | Flush to DB; clear Redis key |

**LangGraph Checkpointer**: Uses `AsyncPostgresSaver` — each `StateSnapshot` is stored in `checkpoint_blobs` table with thread_id = job_id, allowing mid-pipeline resume on process restart.

---

## Tier 2 — Episodic Memory (PostgreSQL)

Structured relational storage for job-level and execution-level data. Agents write to this layer via the API (not directly to DB).

### Data Written Per Job

```mermaid
sequenceDiagram
    participant AG as Agent
    participant SVC as Service Layer
    participant DB as PostgreSQL

    Note over AG,DB: Episodic Memory Write Pattern

    AG->>SVC: append_agent_log(job_id, agent_type, tokens, cost, message)
    SVC->>DB: INSERT agent_logs (partitioned by week)

    AG->>SVC: record_source(job_id, url, title, relevance_score)
    SVC->>DB: INSERT sources

    AG->>SVC: update_job_progress(job_id, percent, status)
    SVC->>DB: UPDATE research_jobs

    AG->>SVC: save_report_draft(job_id, content, citations)
    SVC->>DB: INSERT/UPDATE reports
```

### Memory Fields in `research_jobs`

| Column | Type | Memory Purpose |
|---|---|---|
| `orchestration_plan` | JSONB | Planner's complete plan — referenced by all agents |
| `state_checkpoint` | JSONB | Latest LangGraph state snapshot |
| `quality_score` | NUMERIC | Final quality assessment from Insight Agent |
| `total_tokens_used` | INTEGER | Running token count across all agents |
| `total_cost_usd` | NUMERIC | Running cost total |
| `error_message` | TEXT | Last failure description |
| `retry_count` | SMALLINT | Number of pipeline-level retries |

---

## Tier 3 — Semantic Memory (Qdrant)

Vector store for all content that agents need to retrieve via semantic similarity.

### Collections Design

```mermaid
flowchart LR
    subgraph QDRANT["Qdrant Collections (one per org)"]

        COL1["org_{org_id}_sources\nSource content chunks\nVector: 3072-dim (ada-3-large)\nPayload: source_id, job_id, chunk_index\nurl, title, tier, published_date"]

        COL2["org_{org_id}_claims\nVerified claim embeddings\nVector: 3072-dim\nPayload: claim_id, job_id, status\nconfidence_score, claim_type"]

        COL3["org_{org_id}_literature\nAcademic paper chunks\nVector: 3072-dim\nPayload: paper_id, doi, authors\nyear, journal, level_of_evidence"]

        COL4["org_{org_id}_reports\nFinal report paragraphs\nVector: 3072-dim\nPayload: report_id, job_id\nsection, paragraph_index"]
    end
```

### Chunking Strategy

| Collection | Chunk Size | Overlap | Metadata Included |
|---|---|---|---|
| `sources` | 512 tokens | 50 tokens | source_id, url, title, tier, relevance_score, job_id |
| `literature` | 384 tokens | 64 tokens | paper_id, doi, year, journal, level_of_evidence, job_id |
| `claims` | Full claim text | N/A | claim_id, status, confidence_score, job_id |
| `reports` | 256 tokens | 32 tokens | report_id, section, job_id |

### Retrieval Patterns Per Agent

| Agent | Retrieval Pattern | Filter |
|---|---|---|
| Research Agent | Similarity search for sub-task queries | `job_id`, `org_id` |
| Verification Agent | Similarity search for claim corroboration | `org_id`, `tier >= 1` |
| Contradiction Agent | Dense retrieval of semantically similar claims | `job_id`, `confidence_score >= 0.5` |
| Insight Agent | Cross-job retrieval for pattern recognition | `org_id`, `quality_score >= 0.8` |
| Report Agent | Ordered retrieval for citation lookup | `job_id`, section filter |

---

## Tier 4 — Long-Term Memory (Cross-Job Learning)

Accumulated intelligence that improves research quality over time, scoped per organization.

### Research Pattern Cache

```mermaid
flowchart TD
    JOB_DONE[Job Completes\nquality_score >= 0.85] --> EXTRACT

    EXTRACT["Extract successful patterns:\n- Which search queries produced\n  high-relevance sources?\n- Which sub-task decompositions\n  worked well for this domain?\n- Which agent sequences\n  minimized contradictions?"]

    EXTRACT --> STORE["Store in Redis\npattern:{org_id}:{domain}:{pattern_hash}\nTTL: 90 days"]

    STORE --> PLANNER["Planner Agent reads patterns\nat job start:\n'For climate research queries,\nthese sub-task structures\nhave worked best'"]
```

### Domain Knowledge Base

```
PostgreSQL table: domain_knowledge
Columns: org_id, domain, fact, confidence, source_job_ids, last_validated, created_at

- Built from high-confidence verified claims across multiple jobs
- Seeded into Research Agent context for each new job in the same domain
- Invalidated when contradicted by newer evidence (temporal invalidation)
- Example: "As of Q3 2025, global EV market share is 18.2% (±0.3%)" — stored, reused
```

### Human Feedback Integration

```mermaid
flowchart LR
    HUMAN["Human Reviewer\nrates report 1-5 stars\nadds qualitative feedback"]

    HUMAN --> FEEDBACK_DB["report_feedback table\nrating, comment, user_id\nreport_id, created_at"]

    FEEDBACK_DB --> ANALYZER["Feedback Analyzer\n(nightly batch job)\nCompute per-agent\nquality contributions"]

    ANALYZER --> AGENT_PERF["agent_performance_metrics\nPer model, per domain:\navg quality, avg tokens,\navg cost, failure rate"]

    AGENT_PERF --> ROUTER["Model Selection Router\nPlanner uses metrics to\nadjust agent parameters\nfor next job in domain"]
```

---

## Memory Access Control

| Memory Tier | Who Writes | Who Reads | Isolation |
|---|---|---|---|
| Working Memory (State) | All agents (designated fields) | All agents | Job-scoped |
| Episodic (PostgreSQL) | Service layer (API) | All agents via service | Org + Job scoped |
| Semantic (Qdrant) | Research + Lit agents | All agents | Org-scoped collection |
| Long-term (Redis/PG) | Nightly batch + feedback | Planner Agent | Org-scoped keys |

> [!IMPORTANT]
> Cross-org memory access is architecturally impossible — all Qdrant collections, Redis keys, and PostgreSQL queries are namespaced by `org_id`. Agent prompts include org_id in retrieval tool calls.
