# Backend Architecture — Domain Services Design

## Service Architecture Pattern

Each domain service follows the same contract:
- **Constructor injection** of its repository (and any cross-domain services needed)
- **No direct DB session access** — only via repository methods
- **Raises domain-specific exceptions** — never raw SQLAlchemy errors
- **Emits audit events** — every mutating operation triggers an audit log entry
- **Transaction ownership** — the service layer, not the repository, manages transaction boundaries

---

## 1. User Management Service

### Responsibilities
- User registration with email verification flow
- Password management (hash, verify, change, reset)
- Account lifecycle: activate, suspend, lock after brute-force
- API key creation and revocation
- Role-based access checks (delegated to AuthService)

### Service Contract

```mermaid
classDiagram
    class UserService {
        -user_repo: UserRepository
        -org_repo: OrganizationRepository
        -audit_service: AuditService
        -redis: Redis

        +register(data: UserCreate, org_id: UUID) UserResponse
        +get_by_id(user_id: UUID, requester: JWTClaims) UserResponse
        +get_by_email(email: str) User
        +list_users(org_id: UUID, filter: UserFilter) Page~UserResponse~
        +update_profile(user_id: UUID, data: UserUpdate, requester: JWTClaims) UserResponse
        +update_password(user_id: UUID, data: UserPasswordUpdate) None
        +suspend(user_id: UUID, requester: JWTClaims) None
        +delete(user_id: UUID, requester: JWTClaims) None
        +create_api_key(user_id: UUID, data: APIKeyCreate) APIKeyCreatedResponse
        +revoke_api_key(key_id: UUID, user_id: UUID) None
        +record_login_attempt(user_id: UUID, success: bool) None
        +verify_email(token: str) None
    }

    class UserRepository {
        +get(id: UUID) User
        +get_by_email(email: str) User
        +get_by_org(org_id: UUID, filter) list~User~
        +create(data: dict) User
        +update(id: UUID, data: dict) User
        +soft_delete(id: UUID) None
        +increment_failed_login(id: UUID) None
        +reset_failed_login(id: UUID) None
        +create_api_key(data: dict) APIKey
        +get_api_key_by_hash(hash: str) APIKey
        +revoke_api_key(key_id: UUID) None
    }

    UserService --> UserRepository
    UserService --> AuditService
```

### Account Lock Flow

```mermaid
flowchart TD
    LOGIN[Login Attempt] --> VERIFY{Password Valid?}
    VERIFY -->|Yes| RESET[Reset failed_login_count = 0\nUpdate last_login_at]
    VERIFY -->|No| INCREMENT[Increment failed_login_count]
    INCREMENT --> CHECK{Count >= 5?}
    CHECK -->|No| FAIL[Return 401]
    CHECK -->|Yes| LOCK[Set locked_until = NOW() + 30min\nSend alert email]
    LOCK --> FAIL
    RESET --> TOKEN[Issue token pair]
```

---

## 2. Research Project Management Service

### Responsibilities
- Project CRUD with slug auto-generation
- Member invitation and role management
- Project visibility enforcement (private/org/public)
- Job count cache maintenance
- Soft-archive flow

### Service Contract

```mermaid
classDiagram
    class ProjectService {
        -project_repo: ProjectRepository
        -user_repo: UserRepository
        -audit_service: AuditService

        +create(data: ProjectCreate, owner: JWTClaims) ProjectResponse
        +get(project_id: UUID, requester: JWTClaims) ProjectResponse
        +list(org_id: UUID, requester: JWTClaims, filter: ProjectFilter) Page~ProjectResponse~
        +update(project_id: UUID, data: ProjectUpdate, requester: JWTClaims) ProjectResponse
        +archive(project_id: UUID, requester: JWTClaims) None
        +delete(project_id: UUID, requester: JWTClaims) None
        +invite_member(project_id: UUID, data: MemberInvite, requester: JWTClaims) ProjectMemberResponse
        +remove_member(project_id: UUID, user_id: UUID, requester: JWTClaims) None
        +check_access(project_id: UUID, requester: JWTClaims, min_role: str) None
    }
```

### Visibility Access Matrix

| Visibility | Own Org Members | Other Orgs | Public |
|---|---|---|---|
| `private` | Members only | ❌ | ❌ |
| `org` | All org members | ❌ | ❌ |
| `public` | All org members | ✅ Read | ✅ Read |

### Slug Generation Logic

```
slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip()).strip('-')
# If slug collides within org → append short UUID suffix: "my-project-a3f2"
```

---

## 3. Research Job Service

### Responsibilities
- Job creation with config validation
- Queue dispatch via Redis (priority-weighted sorted set)
- Real-time status update via Redis + WebSocket broadcast
- Job cancellation (Redis task cancellation signal)
- Retry logic with exponential backoff

### Service Contract

```mermaid
classDiagram
    class JobService {
        -job_repo: JobRepository
        -project_service: ProjectService
        -audit_service: AuditService
        -redis: Redis

        +create(project_id: UUID, data: JobCreate, requester: JWTClaims) JobCreatedResponse
        +get(job_id: UUID, requester: JWTClaims) JobResponse
        +list(project_id: UUID, filter: JobFilter, requester: JWTClaims) Page~JobSummary~
        +update_status(job_id: UUID, status: JobStatus, meta: dict) None
        +update_progress(job_id: UUID, percent: int) None
        +cancel(job_id: UUID, requester: JWTClaims) None
        +retry(job_id: UUID, requester: JWTClaims) None
        +complete(job_id: UUID, quality_score: float, tokens: int, cost: Decimal) None
        +fail(job_id: UUID, error_message: str) None
    }
```

### Job Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> QUEUED : create()
    QUEUED --> RUNNING : Agent picks up task
    QUEUED --> CANCELLED : cancel()
    RUNNING --> COMPLETED : complete()
    RUNNING --> FAILED : fail()
    RUNNING --> CANCELLED : cancel()
    FAILED --> RETRYING : retry() if retry_count < max_retries
    RETRYING --> RUNNING : Re-queued
    RETRYING --> FAILED : retry_count exhausted
    COMPLETED --> [*]
    CANCELLED --> [*]
    FAILED --> [*]
```

### Redis Queue Design

```
ZADD task_queue:{priority}  {unix_timestamp_score}  {job_id}
# Priority queues: task_queue:critical, task_queue:high, task_queue:normal, task_queue:low
# Agents ZPOPMIN in order: critical → high → normal → low
```

### Status Broadcast (Redis → WebSocket)

```
PUBLISH ws:job:{job_id}  {"event": "status_update", "status": "RUNNING", "progress": 45}
```

---

## 4. Source Management Service

### Responsibilities
- Source record creation (called by agent workers via internal API)
- Relevance score and metadata updates
- Deduplication via content_hash within a job
- Source exclusion (manual override)
- Bulk source listing with rich filtering

### Service Contract

```mermaid
classDiagram
    class SourceService {
        -source_repo: SourceRepository
        -job_service: JobService

        +create_bulk(job_id: UUID, sources: list~SourceCreate~) list~SourceResponse~
        +get(source_id: UUID) SourceResponse
        +list(job_id: UUID, filter: SourceFilter) Page~SourceResponse~
        +update_status(source_id: UUID, status: SourceStatus, metadata: dict) None
        +update_relevance(source_id: UUID, score: float, chunk_count: int) None
        +exclude(source_id: UUID, requester: JWTClaims) None
        +deduplicate(job_id: UUID) int
    }
```

### Deduplication Strategy

```mermaid
flowchart LR
    NEW[New Source\ncontent_hash = SHA-256(content)]
    CHECK{Hash exists\nin job?}
    NEW --> CHECK
    CHECK -->|Yes| SKIP[Skip insertion\nreturn existing source_id]
    CHECK -->|No| INSERT[INSERT source\nmark status=pending]
    INSERT --> EMBED[Queue for embedding\n→ Qdrant]
```

---

## 5. Report Storage Service

### Responsibilities
- Report creation linked to a job
- Content versioning (each regeneration increments `version`)
- Export orchestration (Markdown → PDF/HTML via Pandoc/WeasyPrint)
- Publish/unpublish lifecycle
- Feedback collection and score aggregation

### Service Contract

```mermaid
classDiagram
    class ReportService {
        -report_repo: ReportRepository
        -job_service: JobService
        -storage: S3Client
        -audit_service: AuditService

        +create(job_id: UUID, data: ReportCreate) ReportResponse
        +get(report_id: UUID, requester: JWTClaims) ReportResponse
        +list(job_id: UUID, requester: JWTClaims) list~ReportSummary~
        +update_content(report_id: UUID, content: str, summary: str, citations: list) ReportResponse
        +complete(report_id: UUID, quality_score: float) ReportResponse
        +export(report_id: UUID, format: ReportFormat) bytes
        +publish(report_id: UUID, requester: JWTClaims) ReportResponse
        +unpublish(report_id: UUID, requester: JWTClaims) ReportResponse
        +add_feedback(report_id: UUID, data: FeedbackCreate, requester: JWTClaims) FeedbackResponse
        +get_average_rating(report_id: UUID) float
        +delete(report_id: UUID, requester: JWTClaims) None
    }
```

### Report Versioning Flow

```mermaid
flowchart TD
    A[Agent generates new content] --> B{Report exists\nfor this job?}
    B -->|No| C[INSERT report version=1\nstatus=generating]
    B -->|Yes| D[UPDATE report\nversion = version + 1\nstatus=generating]
    C & D --> E[Write content\ncitations\nexecutive_summary]
    E --> F[Calculate word_count]
    F --> G[status=completed]
```

---

## 6. Agent Execution Log Service

### Responsibilities
- High-throughput append-only log writes (called by agent workers)
- Batch insert for performance (agent workers buffer locally and flush every 2s)
- Filtered querying with cursor pagination
- Server-Sent Events streaming for real-time log tailing
- Cost aggregation per job, per model, per agent type

### Service Contract

```mermaid
classDiagram
    class AgentLogService {
        -log_repo: AgentLogRepository
        -job_service: JobService
        -redis: Redis

        +append(log: AgentLogCreate) AgentLogResponse
        +append_batch(logs: list~AgentLogCreate~) int
        +get(log_id: UUID) AgentLogResponse
        +list(job_id: UUID, filter: LogFilter) Page~AgentLogResponse~
        +stream(job_id: UUID, filter: LogFilter) AsyncIterator~AgentLogResponse~
        +get_cost_summary(job_id: UUID) CostSummary
        +get_model_usage(org_id: UUID, from_dt: datetime, to_dt: datetime) list~ModelUsage~
    }

    class CostSummary {
        +job_id: UUID
        +total_cost_usd: Decimal
        +total_input_tokens: int
        +total_output_tokens: int
        +by_agent: dict[str, AgentCost]
        +by_model: dict[str, ModelCost]
    }
```

### Log Stream Implementation

```
1. Client connects to GET /jobs/{job_id}/logs/stream (SSE)
2. Service subscribes to Redis channel: ws:job:{job_id}:logs
3. Agent workers PUBLISH to ws:job:{job_id}:logs after each log write
4. SSE handler forwards event to connected client
5. On job completion, emit final "job_status" event and close stream
```

---

## 7. Audit Log Service

### Responsibilities
- Immutable audit trail for all mutating operations
- Called as a side effect inside every service mutating method
- Never throws exceptions — audit failure is logged but doesn't block the primary operation
- Rich filtering for compliance reporting and incident investigation

### Service Contract

```mermaid
classDiagram
    class AuditService {
        -audit_repo: AuditLogRepository

        +log(action: AuditAction, resource_type: str, resource_id: UUID, requester: JWTClaims, request: Request, old_value: dict, new_value: dict, result: str, failure_reason: str) None
        +list(org_id: UUID, filter: AuditFilter) Page~AuditLogResponse~
        +export_csv(org_id: UUID, filter: AuditFilter) bytes
    }
```

### Audit Log Write Pattern

```mermaid
flowchart LR
    SERVICE[Service Method\nmutates data] --> TRY
    TRY{Try primary\noperation} -->|Success| AUDIT_OK[audit_service.log\nresult=success]
    TRY -->|Failure| AUDIT_FAIL[audit_service.log\nresult=failure\nfailure_reason=str(e)]
    AUDIT_OK --> RETURN[Return to caller]
    AUDIT_FAIL --> RAISE[Re-raise original exception]
```

**Key invariant**: Audit writes use a **separate, short-lived DB session** so they commit independently — an audit record is written even if the surrounding transaction rolls back.

---

## Cross-Service Dependency Graph

```mermaid
flowchart TD
    AUDIT[AuditService]
    USER[UserService]
    ORG[OrganizationService]
    PROJECT[ProjectService]
    JOB[JobService]
    SOURCE[SourceService]
    REPORT[ReportService]
    AGENTLOG[AgentLogService]

    USER --> ORG
    USER --> AUDIT
    PROJECT --> USER
    PROJECT --> AUDIT
    JOB --> PROJECT
    JOB --> AUDIT
    SOURCE --> JOB
    REPORT --> JOB
    REPORT --> AUDIT
    AGENTLOG --> JOB
```

**Rule**: Dependency arrows flow downward only. No circular dependencies.

---

## Redis Usage by Service

| Service | Key Pattern | Operation | TTL |
|---|---|---|---|
| AuthService | `refresh:{user_id}:{jti}` | SETEX on login | 7 days |
| AuthService | `blocklist:{jti}` | SETEX on logout | Until exp |
| UserService | `user_lock:{user_id}` | SETEX on lockout | 30 min |
| UserService | `email_verify:{token}` | SETEX on register | 24 hours |
| JobService | `task_queue:{priority}` | ZADD / ZPOPMIN | — |
| JobService | `job_status:{job_id}` | HSET | Session TTL |
| AgentLogService | `ws:job:{job_id}:logs` | PUBLISH (channel) | — |
| RateLimiter | `ratelimit:{user_id}:{window}` | INCR + EXPIRE | Per window |
