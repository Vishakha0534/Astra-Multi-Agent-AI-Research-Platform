# 5. Database Design

## Storage Strategy Overview

| Store | Technology | Data Type | Retention |
|---|---|---|---|
| Relational | PostgreSQL 16 | Users, sessions, reports, audit logs | Permanent |
| Cache | Redis 7 | Session context, rate limits, pub/sub | TTL-based |
| Vector | Qdrant | Embeddings, semantic search | Permanent |
| Object | S3-compatible | Files, PDFs, exported reports | Permanent |

---

## PostgreSQL Entity-Relationship Diagram

```mermaid
erDiagram
    USERS {
        uuid id PK
        varchar email UK
        varchar username UK
        varchar password_hash
        varchar full_name
        UserRole role
        boolean is_active
        boolean is_verified
        jsonb preferences
        timestamp created_at
        timestamp updated_at
        timestamp last_login_at
    }

    ORGANIZATIONS {
        uuid id PK
        varchar name UK
        varchar slug UK
        jsonb settings
        int max_sessions_per_day
        int token_budget_daily
        timestamp created_at
    }

    ORG_MEMBERSHIPS {
        uuid id PK
        uuid org_id FK
        uuid user_id FK
        OrgRole role
        timestamp joined_at
    }

    API_KEYS {
        uuid id PK
        uuid user_id FK
        varchar key_hash UK
        varchar name
        list scopes
        boolean is_active
        timestamp expires_at
        timestamp created_at
        timestamp last_used_at
    }

    RESEARCH_SESSIONS {
        uuid id PK
        uuid user_id FK
        uuid org_id FK
        varchar title
        text original_query
        SessionStatus status
        jsonb config
        jsonb orchestration_plan
        float total_cost_usd
        int total_tokens_used
        int duration_seconds
        int quality_score
        timestamp created_at
        timestamp completed_at
    }

    RESEARCH_TASKS {
        uuid id PK
        uuid session_id FK
        uuid parent_task_id FK
        AgentType agent_type
        TaskStatus status
        text input_payload
        text output_payload
        varchar model_used
        int input_tokens
        int output_tokens
        float cost_usd
        int attempt_count
        text error_message
        timestamp started_at
        timestamp completed_at
    }

    AGENT_MESSAGES {
        uuid id PK
        uuid session_id FK
        uuid task_id FK
        varchar sender_agent_id
        varchar receiver_agent_id
        MessageType message_type
        text content
        jsonb tool_calls
        jsonb tool_results
        varchar trace_id
        timestamp created_at
    }

    RESEARCH_REPORTS {
        uuid id PK
        uuid session_id FK
        uuid user_id FK
        varchar title
        text markdown_content
        text executive_summary
        jsonb citations
        jsonb metadata
        float quality_score
        varchar export_format
        varchar file_path
        timestamp created_at
        timestamp updated_at
    }

    KNOWLEDGE_DOCUMENTS {
        uuid id PK
        uuid org_id FK
        varchar filename
        varchar content_type
        bigint file_size_bytes
        varchar s3_key
        varchar qdrant_collection
        int chunk_count
        jsonb metadata
        varchar status
        timestamp uploaded_at
        timestamp indexed_at
    }

    MODEL_REGISTRY {
        uuid id PK
        varchar provider
        varchar model_name UK
        varchar display_name
        int context_window_tokens
        float cost_per_input_token
        float cost_per_output_token
        int avg_latency_ms
        float reliability_score
        boolean is_active
        jsonb capabilities
        jsonb default_params
        timestamp updated_at
    }

    USAGE_LOGS {
        uuid id PK
        uuid user_id FK
        uuid session_id FK
        varchar model_name
        int input_tokens
        int output_tokens
        float cost_usd
        int latency_ms
        boolean success
        varchar error_code
        timestamp logged_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        varchar action
        varchar resource_type
        uuid resource_id
        jsonb old_value
        jsonb new_value
        varchar ip_address
        varchar user_agent
        timestamp created_at
    }

    USERS ||--o{ ORG_MEMBERSHIPS : "belongs to"
    ORGANIZATIONS ||--o{ ORG_MEMBERSHIPS : "has"
    USERS ||--o{ API_KEYS : "owns"
    USERS ||--o{ RESEARCH_SESSIONS : "creates"
    ORGANIZATIONS ||--o{ RESEARCH_SESSIONS : "owns"
    RESEARCH_SESSIONS ||--o{ RESEARCH_TASKS : "contains"
    RESEARCH_TASKS ||--o{ RESEARCH_TASKS : "parent_of"
    RESEARCH_SESSIONS ||--o{ AGENT_MESSAGES : "records"
    RESEARCH_TASKS ||--o{ AGENT_MESSAGES : "logs"
    RESEARCH_SESSIONS ||--o| RESEARCH_REPORTS : "produces"
    ORGANIZATIONS ||--o{ KNOWLEDGE_DOCUMENTS : "uploads"
    USERS ||--o{ USAGE_LOGS : "generates"
    RESEARCH_SESSIONS ||--o{ USAGE_LOGS : "tracks"
    USERS ||--o{ AUDIT_LOGS : "audited"
```

---

## Redis Data Structures

```mermaid
flowchart TD
    subgraph REDIS["Redis 7 Key Space"]
        subgraph Sessions["Session Cache"]
            S1["session:{id}:state → Hash\n(status, config, metadata)"]
            S2["session:{id}:context → Hash\n(merged chunks, citations)"]
            S3["session:{id}:messages → List\n(recent message history)"]
        end

        subgraph RateLimit["Rate Limiting"]
            R1["ratelimit:user:{uid}:api → Sorted Set\n(sliding window counters)"]
            R2["ratelimit:user:{uid}:tokens → String\n(daily token counter)"]
        end

        subgraph AgentState["Agent Coordination"]
            A1["agent:{id}:heartbeat → String\n(TTL: 30s)"]
            A2["agent:{id}:lock:{task_id} → String\n(distributed lock, TTL: 60s)"]
            A3["task_queue:{priority} → Sorted Set\n(pending task IDs by priority)"]
        end

        subgraph ModelCache["Model Response Cache"]
            M1["llm_cache:{prompt_hash} → Hash\n(response, tokens, TTL: 24h)"]
            M2["model_health:{provider} → Hash\n(uptime, latency, error_rate)"]
        end

        subgraph PubSub["Pub/Sub Channels"]
            P1["task.dispatch.{agent_type}"]
            P2["task.result.{task_id}"]
            P3["session.status.{session_id}"]
        end
    end
```

---

## Qdrant Vector Collections

| Collection | Purpose | Vector Dim | Distance | Fields |
|---|---|---|---|---|
| `research_chunks` | Document chunks from research outputs | 1536 | Cosine | session_id, agent_id, timestamp, topic_tags |
| `knowledge_base` | Org-uploaded knowledge documents | 1536 | Cosine | org_id, document_id, chunk_index, source |
| `fact_claims` | Fact-check verified claims | 1536 | Cosine | session_id, verified, confidence, source |
| `agent_memories` | Episodic memories per agent | 1536 | Cosine | agent_type, session_id, importance_score |

---

## Database Indexes

```mermaid
flowchart LR
    subgraph PG_Indexes["PostgreSQL Critical Indexes"]
        I1["research_sessions\n(user_id, status, created_at)"]
        I2["research_tasks\n(session_id, status, agent_type)"]
        I3["agent_messages\n(session_id, created_at)"]
        I4["usage_logs\n(user_id, logged_at, model_name)"]
        I5["research_sessions\n(org_id, created_at DESC)"]
    end
```

---

## Data Partitioning Strategy

| Table | Partition Key | Strategy | Retention |
|---|---|---|---|
| `usage_logs` | `logged_at` | Range (monthly) | 12 months active, archive after |
| `audit_logs` | `created_at` | Range (quarterly) | 7 years (compliance) |
| `agent_messages` | `created_at` | Range (weekly) | 90 days active |
| `research_tasks` | `session_id` hash | Hash (16 shards) | Permanent |
