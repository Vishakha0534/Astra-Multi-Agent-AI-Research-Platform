# 4. Agent Communication Workflow

## Communication Layers

Agent communication is implemented in **three layers**:

| Layer | Technology | Purpose |
|---|---|---|
| **Async Messaging** | Redis Pub/Sub | Real-time agent-to-agent event propagation |
| **State Sharing** | Redis Hash + LangGraph Checkpointer | Shared working memory within a session |
| **Persistent Protocol** | PostgreSQL | Durable audit trail of all agent messages |

---

## Message Envelope Schema

```mermaid
classDiagram
    class MessageEnvelope {
        +str message_id
        +str session_id
        +str task_id
        +str sender_agent_id
        +str receiver_agent_id
        +MessageType message_type
        +int priority
        +datetime timestamp
        +int ttl_seconds
        +MessagePayload payload
        +dict headers
        +str correlation_id
        +str trace_id
    }

    class MessagePayload {
        +str content
        +str content_type
        +dict tool_calls
        +dict tool_results
        +dict artifacts
        +list~str~ citations
        +float confidence_score
    }

    class MessageType {
        <<enumeration>>
        TASK_DISPATCH
        TASK_RESULT
        CONTEXT_REQUEST
        CONTEXT_RESPONSE
        QUALITY_REVIEW
        REVISION_REQUEST
        ERROR_REPORT
        HEARTBEAT
        SESSION_COMPLETE
    }

    MessageEnvelope "1" --> "1" MessagePayload
    MessageEnvelope "1" --> "1" MessageType
```

---

## End-to-End Research Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Next.js Frontend
    participant API as FastAPI Gateway
    participant ORC as Orchestrator Agent
    participant RA as Research Agent
    participant MA as Memory Agent
    participant FA as Fact-Check Agent
    participant SA as Synthesis Agent
    participant CA as Critique Agent
    participant REP as Report Agent
    participant DB as PostgreSQL
    participant VS as Qdrant Vector Store
    participant WS as WebSocket Channel

    User->>FE: Submit research query
    FE->>API: POST /research/sessions {query, config}
    API->>DB: INSERT research_session (status=PENDING)
    API->>ORC: Dispatch session via Redis PUBLISH
    API-->>FE: 202 Accepted {session_id, ws_url}
    FE->>WS: Subscribe to session:{session_id}

    ORC->>ORC: GPT-4o: Decompose query into sub-tasks
    ORC->>DB: UPDATE session (status=RUNNING)
    ORC->>WS: EMIT {event: "orchestration_started"}

    par Research Phase (Parallel)
        ORC->>RA: DISPATCH sub-task-1 (domain A)
        ORC->>RA: DISPATCH sub-task-2 (domain B)
        ORC->>RA: DISPATCH sub-task-3 (domain C)
    end

    RA->>MA: GET session context + relevant embeddings
    MA->>VS: similarity_search(query_embedding, top_k=10)
    VS-->>MA: relevant document chunks
    MA-->>RA: MemoryContext

    RA->>RA: Gemini 2.5 Pro: Research each domain
    RA->>MA: STORE result chunks
    MA->>VS: upsert embeddings (result vectors)
    RA->>WS: EMIT {event: "research_partial", progress: 33%}

    RA->>FA: DISPATCH fact-check(claims)
    FA->>VS: vector_search(claim_embeddings)
    FA->>FA: Qwen 3: Validate claims
    FA-->>SA: Verified facts + citations

    SA->>MA: GET all session chunks
    SA->>SA: Claude Sonnet: Synthesize findings
    SA->>WS: EMIT {event: "synthesis_complete"}

    SA->>CA: REQUEST quality review
    CA->>CA: DeepSeek R1: Score logic, coherence, accuracy
    CA-->>ORC: QualityReport {score: 0.92, issues: []}

    ORC->>ORC: Quality Gate: score >= 0.85 PASS
    ORC->>REP: DISPATCH format_report
    REP->>REP: Claude Sonnet: Structure Markdown/PDF
    REP->>DB: INSERT research_report
    REP->>WS: EMIT {event: "report_ready", report_id}

    FE->>API: GET /research/reports/{report_id}
    API->>DB: SELECT report
    API-->>FE: Report payload
    FE-->>User: Render final research output
```

---

## Redis Channel Architecture

```mermaid
flowchart TB
    subgraph Channels["Redis Pub/Sub Channels"]
        C1["task.dispatch.{agent_type}"]
        C2["task.result.{task_id}"]
        C3["session.status.{session_id}"]
        C4["agent.heartbeat.{agent_id}"]
        C5["quality.review.{session_id}"]
        C6["revision.request.{task_id}"]
        C7["session.complete.{session_id}"]
    end

    subgraph Producers["Channel Producers"]
        ORC[Orchestrator] -->|publishes| C1
        RA[Research Agent] -->|publishes| C2
        FA[Fact-Check] -->|publishes| C2
        SA[Synthesis] -->|publishes| C3
        CA[Critique] -->|publishes| C5
        ALL[All Agents] -->|publishes| C4
    end

    subgraph Consumers["Channel Consumers"]
        C1 -->|subscribes| RA
        C1 -->|subscribes| FA
        C2 -->|subscribes| ORC
        C3 -->|subscribes| WSGATEWAY[WebSocket Gateway]
        C4 -->|subscribes| HEALTHMON[Health Monitor]
        C5 -->|subscribes| ORC
        C7 -->|subscribes| WSGATEWAY
    end
```

---

## Agent Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> IDLE : Agent instantiated

    IDLE --> INITIALIZING : Task received
    INITIALIZING --> CONTEXT_LOADING : Load memory context
    CONTEXT_LOADING --> EXECUTING : Context ready
    EXECUTING --> TOOL_CALLING : Invoke tools
    TOOL_CALLING --> EXECUTING : Tool result returned
    EXECUTING --> WAITING : Waiting for sub-agent result
    WAITING --> EXECUTING : Sub-agent responded
    EXECUTING --> VALIDATING : Output generated
    VALIDATING --> COMPLETED : Validation passed
    VALIDATING --> RETRYING : Validation failed (retry < 3)
    RETRYING --> EXECUTING : Retry attempt
    RETRYING --> FAILED : Max retries exceeded
    FAILED --> IDLE : Error reported to orchestrator
    COMPLETED --> IDLE : Result dispatched
```

---

## Inter-Agent Trust Model

| Communication Path | Trust Level | Verification |
|---|---|---|
| Orchestrator → Research Agent | Full Trust | Shared session token |
| Research Agent → Memory Agent | Full Trust | Internal gRPC mTLS |
| Fact-Check → External KB | Limited Trust | API key + schema validation |
| Any Agent → LLM Provider | Untrusted Network | TLS + API key per provider |
| Agent → PostgreSQL | Service Trust | Service account + TLS |
| Agent → Redis | Internal Trust | Redis AUTH + ACLs |
