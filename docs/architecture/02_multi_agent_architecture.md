# 2. Multi-Agent Architecture

## Agent Design Philosophy

Each agent in the platform is an autonomous, stateful unit that:
- Receives structured tasks from the LangGraph orchestrator
- Maintains its own working memory and tool access
- Communicates results via a typed message protocol
- Can spawn sub-agents for parallelism (fan-out pattern)

---

## Agent Taxonomy

| Agent | Role | Primary Model | Tools |
|---|---|---|---|
| **Orchestrator Agent** | Decomposes research goals, routes sub-tasks | GPT-4o | Task planner, DAG builder |
| **Research Agent** | Retrieves and summarizes domain knowledge | Gemini 2.5 Pro | Web search, RAG, document loader |
| **Synthesis Agent** | Merges multi-source findings into coherent output | Claude Sonnet | Merge engine, citation formatter |
| **Critique Agent** | Evaluates quality, logic, and factual accuracy | DeepSeek R1 | Scorer, logic checker |
| **Fact-Check Agent** | Validates claims against trusted knowledge base | Qwen 3 | Vector search, external KB |
| **Memory Agent** | Manages context, episodic memory, and retrieval | GPT-4o | Qdrant write/read, Redis cache |
| **Code Agent** | Generates and executes code for data analysis | DeepSeek R1 | Code interpreter, sandboxed exec |
| **Report Agent** | Structures final research output into formats | Claude Sonnet | Template engine, PDF/Markdown export |

---

## Agent State Schema

```mermaid
classDiagram
    class AgentState {
        +str session_id
        +str task_id
        +AgentType agent_type
        +TaskStatus status
        +dict input_payload
        +dict output_payload
        +list~Message~ message_history
        +MemoryContext memory_context
        +ModelConfig model_config
        +datetime created_at
        +datetime updated_at
        +int retry_count
        +dict metadata
    }

    class Message {
        +str id
        +str role
        +str content
        +str agent_id
        +datetime timestamp
        +dict tool_calls
        +dict tool_results
    }

    class MemoryContext {
        +str session_id
        +list~str~ relevant_chunks
        +dict episodic_summary
        +int token_budget
    }

    class ModelConfig {
        +str provider
        +str model_name
        +float temperature
        +int max_tokens
        +dict provider_params
    }

    AgentState "1" --> "*" Message
    AgentState "1" --> "1" MemoryContext
    AgentState "1" --> "1" ModelConfig
```

---

## LangGraph Workflow DAG

```mermaid
flowchart TD
    START([User Research Query]) --> INTAKE[Intake Node\nValidate & Classify Query]
    INTAKE --> DECOMPOSE[Orchestrator Agent\nDecompose into Sub-Tasks]

    DECOMPOSE --> BRANCH{Task Type?}

    BRANCH -->|Retrieval Required| RESEARCH[Research Agent\nRAG + Web Search]
    BRANCH -->|Code Analysis| CODE[Code Agent\nSandboxed Execution]
    BRANCH -->|Data Synthesis| SYNTH_DIRECT[Synthesis Agent]

    RESEARCH --> FANOUT{Parallel Sub-Tasks}
    FANOUT --> R1[Research Agent\nInstance 1]
    FANOUT --> R2[Research Agent\nInstance 2]
    FANOUT --> R3[Research Agent\nInstance 3]

    R1 & R2 & R3 --> MERGE[Memory Agent\nMerge + Deduplicate Results]

    CODE --> MERGE
    SYNTH_DIRECT --> MERGE

    MERGE --> FACT[Fact-Check Agent\nValidate Claims vs Knowledge Base]
    FACT --> CRITIQUE[Critique Agent\nQuality Score + Logical Review]

    CRITIQUE --> QUALITY{Quality Gate\nScore ≥ 0.85?}
    QUALITY -->|Pass| SYNTHESIZE[Synthesis Agent\nCompose Final Report]
    QUALITY -->|Fail| REVISION[Revision Loop\nIdentify Weak Sections]
    REVISION --> DECOMPOSE

    SYNTHESIZE --> REPORT[Report Agent\nFormat + Export]
    REPORT --> STORE[Persist to PostgreSQL\n+ Index in Qdrant]
    STORE --> NOTIFY[Notify User via WebSocket]
    NOTIFY --> END([Deliver Research Output])
```

---

## Agent Communication Protocol

```mermaid
sequenceDiagram
    participant ORC as Orchestrator Agent
    participant RA as Research Agent
    participant MA as Memory Agent
    participant FA as Fact-Check Agent
    participant SA as Synthesis Agent
    participant REDIS as Redis Pub/Sub
    participant PG as PostgreSQL

    ORC->>REDIS: PUBLISH task.research.{task_id}
    REDIS-->>RA: task received
    RA->>MA: GET relevant_context(query)
    MA->>REDIS: HGET session:{session_id}:context
    REDIS-->>MA: cached context
    MA-->>RA: MemoryContext

    RA->>RA: Execute LLM call (Gemini 2.5 Pro)
    RA->>MA: STORE result_chunk
    MA->>REDIS: HSET session:{session_id}:chunks
    RA->>REDIS: PUBLISH task.complete.{task_id}

    REDIS-->>FA: trigger fact-check
    FA->>MA: GET vector_search(claims)
    MA-->>FA: verified sources

    FA->>REDIS: PUBLISH task.factcheck.complete.{task_id}
    REDIS-->>SA: trigger synthesis

    SA->>MA: GET all_chunks(session_id)
    MA-->>SA: merged context
    SA->>SA: Execute LLM call (Claude Sonnet)
    SA->>PG: INSERT research_report
    SA->>REDIS: PUBLISH session.complete.{session_id}
```

---

## Agent Parallelism Model

```mermaid
flowchart LR
    subgraph FanOut["Fan-Out Pattern"]
        ORCH[Orchestrator] --> T1[Sub-Task 1]
        ORCH --> T2[Sub-Task 2]
        ORCH --> T3[Sub-Task 3]
        T1 & T2 & T3 --> JOIN[Join Node]
    end

    subgraph Pipeline["Pipeline Pattern"]
        P1[Research] --> P2[Fact-Check] --> P3[Synthesis] --> P4[Report]
    end

    subgraph Loop["Revision Loop"]
        L1[Generate] --> L2{Quality Check}
        L2 -->|Fail| L3[Revise]
        L3 --> L1
        L2 -->|Pass| L4[Finalize]
    end
```

---

## Agent Failure & Recovery

| Failure Mode | Detection | Recovery Strategy |
|---|---|---|
| LLM API timeout | Async timeout (30s) | Retry with exponential backoff (max 3x) |
| Model rate limit | 429 HTTP status | Failover to secondary model |
| Agent crash | Heartbeat miss | Restart from last LangGraph checkpoint |
| Invalid output | Pydantic schema validation | Prompt re-injection with error context |
| Context overflow | Token count check | Summarize and truncate via Memory Agent |
| Circular loop | Max iteration counter | Force-exit, escalate to Orchestrator |
