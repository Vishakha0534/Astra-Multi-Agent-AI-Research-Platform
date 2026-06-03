# 6. API Design

## API Design Principles

- **RESTful + WebSocket Hybrid**: REST for CRUD and control; WebSocket for real-time streaming
- **OpenAPI 3.1 First**: All endpoints auto-documented via FastAPI
- **Versioned URLs**: `/api/v1/` prefix for all routes
- **Consistent Envelope**: All responses wrapped in a standard envelope
- **Idempotent Operations**: POST requests with idempotency keys for safe retries
- **Cursor Pagination**: All list endpoints use cursor-based pagination

---

## Standard Response Envelope

```mermaid
classDiagram
    class SuccessResponse {
        +str status = "success"
        +T data
        +Meta meta
        +str trace_id
        +datetime timestamp
    }

    class ErrorResponse {
        +str status = "error"
        +ErrorDetail error
        +str trace_id
        +datetime timestamp
    }

    class ErrorDetail {
        +str code
        +str message
        +dict field_errors
        +str doc_url
    }

    class Meta {
        +int total
        +str next_cursor
        +str prev_cursor
        +int page_size
    }
```

---

## API Surface Map

```mermaid
flowchart TD
    API["/api/v1"] --> AUTH["/auth"]
    API --> USERS["/users"]
    API --> ORGS["/organizations"]
    API --> SESSIONS["/research/sessions"]
    API --> REPORTS["/research/reports"]
    API --> DOCS["/knowledge"]
    API --> MODELS["/models"]
    API --> AGENTS["/agents"]
    API --> HEALTH["/health"]
    API --> METRICS["/metrics"]
    API --> WS["/ws"]

    AUTH --> A1["POST /register"]
    AUTH --> A2["POST /login"]
    AUTH --> A3["POST /refresh"]
    AUTH --> A4["POST /logout"]
    AUTH --> A5["POST /api-keys"]

    SESSIONS --> S1["POST / — Create session"]
    SESSIONS --> S2["GET / — List sessions"]
    SESSIONS --> S3["GET /{id} — Get session detail"]
    SESSIONS --> S4["DELETE /{id} — Cancel session"]
    SESSIONS --> S5["GET /{id}/tasks — List tasks"]
    SESSIONS --> S6["GET /{id}/messages — Agent messages"]

    REPORTS --> R1["GET /{id} — Get report"]
    REPORTS --> R2["GET /{id}/export — Download PDF/MD"]
    REPORTS --> R3["POST /{id}/feedback — Rate report"]

    DOCS --> D1["POST /upload — Upload document"]
    DOCS --> D2["GET / — List documents"]
    DOCS --> D3["DELETE /{id} — Remove document"]
    DOCS --> D4["POST /search — Semantic search"]

    MODELS --> M1["GET / — List available models"]
    MODELS --> M2["GET /health — Model health status"]
    MODELS --> M3["GET /usage — Token usage stats"]

    WS --> W1["/ws/sessions/{id} — Real-time events"]
    WS --> W2["/ws/agents — Agent monitor stream"]
```

---

## Core API Endpoints Specification

### Research Sessions

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/research/sessions` | Create and start a new research session | Bearer |
| `GET` | `/api/v1/research/sessions` | List user's sessions (paginated) | Bearer |
| `GET` | `/api/v1/research/sessions/{session_id}` | Get full session details and status | Bearer |
| `DELETE` | `/api/v1/research/sessions/{session_id}` | Cancel a running session | Bearer |
| `GET` | `/api/v1/research/sessions/{session_id}/tasks` | List all agent tasks in session | Bearer |
| `GET` | `/api/v1/research/sessions/{session_id}/messages` | Retrieve agent message audit trail | Bearer |

### Create Session Request/Response

```mermaid
classDiagram
    class CreateSessionRequest {
        +str title
        +str query
        +ResearchConfig config
        +str idempotency_key
    }

    class ResearchConfig {
        +list~str~ enabled_agents
        +ModelPreferences model_preferences
        +int max_tokens_budget
        +int quality_threshold
        +bool enable_fact_checking
        +bool enable_code_execution
        +str output_format
        +int timeout_seconds
    }

    class CreateSessionResponse {
        +str session_id
        +str status
        +str ws_url
        +datetime estimated_completion
    }

    CreateSessionRequest "1" --> "1" ResearchConfig
```

---

## WebSocket Event Protocol

```mermaid
sequenceDiagram
    participant FE as Frontend Client
    participant WS as WebSocket Gateway
    participant REDIS as Redis Pub/Sub

    FE->>WS: WS Connect /ws/sessions/{session_id}
    WS-->>FE: {"event": "connected", "session_id": "..."}

    REDIS-->>WS: session.status PUBLISH
    WS-->>FE: {"event": "status_update", "status": "RUNNING", "progress": 10}

    REDIS-->>WS: task.result PUBLISH
    WS-->>FE: {"event": "agent_result", "agent": "research", "partial": true, "content": "..."}

    REDIS-->>WS: session.status PUBLISH
    WS-->>FE: {"event": "status_update", "status": "SYNTHESIZING", "progress": 75}

    REDIS-->>WS: session.complete PUBLISH
    WS-->>FE: {"event": "complete", "report_id": "...", "quality_score": 0.92}

    FE->>WS: WS Disconnect
```

### WebSocket Event Types

| Event | Direction | Payload |
|---|---|---|
| `connected` | Server → Client | `{session_id, user_id}` |
| `status_update` | Server → Client | `{status, progress_percent, message}` |
| `agent_started` | Server → Client | `{agent_type, task_id}` |
| `agent_result` | Server → Client | `{agent_type, task_id, partial, content}` |
| `quality_report` | Server → Client | `{score, issues[], passed}` |
| `complete` | Server → Client | `{report_id, quality_score, duration_s}` |
| `error` | Server → Client | `{code, message, recoverable}` |
| `ping` | Client → Server | `{}` |
| `cancel` | Client → Server | `{reason}` |

---

## Rate Limiting Strategy

```mermaid
flowchart LR
    REQ[API Request] --> RATELIMITER[Rate Limiter Middleware]

    RATELIMITER --> CHECK1{API Key\nRate Limit}
    CHECK1 -->|Exceeded| RESP429A[429 Too Many Requests\n+ Retry-After header]
    CHECK1 -->|OK| CHECK2{Token Budget\nLimit}
    CHECK2 -->|Exceeded| RESP429B[429 Token Budget Exhausted\n+ X-Budget-Reset header]
    CHECK2 -->|OK| HANDLER[Request Handler]

    subgraph Limits["Rate Limit Tiers"]
        T1["Free Tier\n10 sessions/day\n50K tokens/day"]
        T2["Pro Tier\n100 sessions/day\n500K tokens/day"]
        T3["Enterprise\nCustom limits\nUnlimited orgs"]
    end
```

---

## API Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI Gateway
    participant AUTH as Auth Service
    participant REDIS as Redis
    participant PG as PostgreSQL

    Client->>API: POST /auth/login {email, password}
    API->>AUTH: Validate credentials
    AUTH->>PG: SELECT user WHERE email=?
    PG-->>AUTH: User record
    AUTH->>AUTH: bcrypt verify password
    AUTH->>AUTH: Generate JWT access_token (15min) + refresh_token (7d)
    AUTH->>REDIS: SETEX refresh:{user_id}:{jti} 7d
    AUTH-->>API: {access_token, refresh_token}
    API-->>Client: 200 OK {tokens}

    Client->>API: GET /research/sessions\nAuthorization: Bearer {access_token}
    API->>AUTH: Verify JWT signature + expiry
    AUTH->>AUTH: Decode claims {user_id, role, org_id}
    AUTH-->>API: Validated claims
    API->>PG: Query with user_id scope
    API-->>Client: 200 OK {data}

    Client->>API: POST /auth/refresh {refresh_token}
    API->>REDIS: GET refresh:{user_id}:{jti}
    REDIS-->>API: Token exists + not revoked
    API->>AUTH: Issue new access_token
    API-->>Client: 200 OK {new_access_token}
```
