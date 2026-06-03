# Backend Architecture — Request/Response Schemas

> All schemas use **Pydantic v2** semantics.
> `model_config = ConfigDict(from_attributes=True)` is set on all response models.
> Timestamps are always `datetime` (UTC-aware).

---

## Base Models

```python
# app/core/schemas.py

class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime

class SoftDeleteMixin(BaseModel):
    deleted_at: datetime | None = None

class PaginatedResponse(BaseModel, Generic[T]):
    status: Literal["success"] = "success"
    data: list[T]
    meta: PaginationMeta
    trace_id: str
    timestamp: datetime

class PaginationMeta(BaseModel):
    total: int
    next_cursor: str | None
    prev_cursor: str | None
    page_size: int

class SingleResponse(BaseModel, Generic[T]):
    status: Literal["success"] = "success"
    data: T
    trace_id: str
    timestamp: datetime

class ErrorDetail(BaseModel):
    code: str
    message: str
    field_errors: dict[str, list[str]] | None = None
    doc_url: str | None = None

class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error: ErrorDetail
    trace_id: str
    timestamp: datetime
```

---

## Auth Schemas

```python
# app/domain/auth/schemas.py

class RegisterRequest(BaseModel):
    org_name:   str = Field(min_length=2, max_length=255)
    email:      EmailStr
    username:   str = Field(min_length=3, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    full_name:  str = Field(min_length=2, max_length=255)
    password:   str = Field(min_length=10, max_length=128)

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    Literal["Bearer"] = "Bearer"
    expires_in:    int  # seconds until access_token expiry

class RegisterResponse(BaseModel):
    user_id: UUID
    email:   str
    message: str

class JWTClaims(BaseModel):
    sub:     str          # user UUID
    email:   str
    role:    UserRole
    org_id:  str
    scopes:  list[str]
    jti:     str          # JWT ID (for revocation)
    iat:     int
    exp:     int
```

---

## User Schemas

```python
# app/domain/users/schemas.py

class UserCreate(BaseModel):
    email:     EmailStr
    username:  str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=2, max_length=255)
    password:  str = Field(min_length=10, max_length=128)
    role:      UserRole = UserRole.RESEARCHER

class UserUpdate(BaseModel):
    full_name:   str | None = Field(None, min_length=2, max_length=255)
    avatar_url:  AnyHttpUrl | None = None
    preferences: dict[str, Any] | None = None

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password:     str = Field(min_length=10, max_length=128)

class AdminUserUpdate(UserUpdate):
    role:   UserRole | None = None
    status: UserStatus | None = None

class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:        UUID
    email:     str
    username:  str
    full_name: str
    role:      UserRole
    avatar_url: str | None

class UserResponse(UserSummary, TimestampMixin):
    status:            UserStatus
    org_id:            UUID
    email_verified_at: datetime | None
    last_login_at:     datetime | None
    preferences:       dict[str, Any]

class APIKeyCreate(BaseModel):
    name:       str = Field(min_length=1, max_length=100)
    scopes:     list[str] = Field(min_length=1)
    expires_at: datetime | None = None

class APIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:          UUID
    name:        str
    key_prefix:  str
    scopes:      list[str]
    is_active:   bool
    expires_at:  datetime | None
    last_used_at: datetime | None
    created_at:  datetime

class APIKeyCreatedResponse(APIKeyResponse):
    key: str   # Full key — shown only once at creation
```

---

## Organization Schemas

```python
# app/domain/organizations/schemas.py

class OrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r'^[a-z0-9-]+$')

class OrgUpdate(BaseModel):
    name:         str | None = None
    settings:     dict[str, Any] | None = None
    token_budget: int | None = Field(None, ge=1000)

class OrgResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:           UUID
    name:         str
    slug:         str
    plan:         str
    token_budget: int
    is_active:    bool
    created_at:   datetime
```

---

## Project Schemas

```python
# app/domain/projects/schemas.py

class ProjectSettings(BaseModel):
    max_jobs:           int = Field(default=100, ge=1, le=10000)
    default_model:      str = "gemini-2.5-pro"
    quality_threshold:  float = Field(default=0.85, ge=0.0, le=1.0)
    auto_publish:       bool = False

class ProjectCreate(BaseModel):
    title:       str = Field(min_length=3, max_length=500)
    description: str | None = Field(None, max_length=5000)
    visibility:  ProjectVisibility = ProjectVisibility.PRIVATE
    tags:        list[str] = Field(default_factory=list, max_length=20)
    settings:    ProjectSettings = Field(default_factory=ProjectSettings)

class ProjectUpdate(BaseModel):
    title:       str | None = Field(None, min_length=3, max_length=500)
    description: str | None = None
    status:      ProjectStatus | None = None
    visibility:  ProjectVisibility | None = None
    tags:        list[str] | None = None
    settings:    ProjectSettings | None = None

class ProjectResponse(BaseModel, TimestampMixin):
    model_config = ConfigDict(from_attributes=True)
    id:          UUID
    title:       str
    slug:        str
    description: str | None
    status:      ProjectStatus
    visibility:  ProjectVisibility
    tags:        list[str]
    settings:    dict[str, Any]
    job_count:   int
    owner:       UserSummary
    archived_at: datetime | None

class MemberInvite(BaseModel):
    user_id: UUID
    role:    Literal["editor", "viewer"] = "viewer"

class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user:      UserSummary
    role:      str
    joined_at: datetime
```

---

## Research Job Schemas

```python
# app/domain/jobs/schemas.py

class ModelPreferences(BaseModel):
    research:     str | None = None
    synthesis:    str | None = None
    critique:     str | None = None
    factcheck:    str | None = None

class JobConfig(BaseModel):
    enabled_agents:       list[AgentType] = Field(
        default_factory=lambda: list(AgentType)
    )
    model_preferences:    ModelPreferences = Field(default_factory=ModelPreferences)
    max_tokens_budget:    int = Field(default=100000, ge=1000, le=2000000)
    quality_threshold:    float = Field(default=0.85, ge=0.0, le=1.0)
    enable_fact_checking: bool = True
    enable_code_execution: bool = False
    output_format:        ReportFormat = ReportFormat.MARKDOWN
    timeout_seconds:      int = Field(default=600, ge=60, le=3600)

class JobCreate(BaseModel):
    title:        str = Field(min_length=5, max_length=500)
    query:        str = Field(min_length=10, max_length=10000)
    priority:     JobPriority = JobPriority.NORMAL
    config:       JobConfig = Field(default_factory=JobConfig)
    scheduled_at: datetime | None = None

class JobResponse(BaseModel, TimestampMixin):
    model_config = ConfigDict(from_attributes=True)
    id:                 UUID
    project_id:         UUID
    title:              str
    query:              str
    status:             JobStatus
    priority:           JobPriority
    config:             dict[str, Any]
    orchestration_plan: dict[str, Any] | None
    progress_percent:   int
    quality_score:      Decimal | None
    total_tokens_used:  int
    total_cost_usd:     Decimal
    error_message:      str | None
    retry_count:        int
    created_by:         UserSummary
    started_at:         datetime | None
    completed_at:       datetime | None

class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:               UUID
    title:            str
    status:           JobStatus
    priority:         JobPriority
    progress_percent: int
    quality_score:    Decimal | None
    created_at:       datetime

class JobCreatedResponse(BaseModel):
    id:       UUID
    title:    str
    status:   JobStatus
    priority: JobPriority
    ws_url:   str
    created_at: datetime
```

---

## Source Schemas

```python
# app/domain/sources/schemas.py

class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              UUID
    job_id:          UUID
    source_type:     SourceType
    status:          SourceStatus
    title:           str | None
    url:             str | None
    relevance_score: Decimal | None
    chunk_count:     int | None
    content_preview: str | None
    metadata:        dict[str, Any]
    indexed_at:      datetime | None
    created_at:      datetime

class SourceFilter(BaseModel):
    source_type:   SourceType | None = None
    status:        SourceStatus | None = None
    min_relevance: float | None = Field(None, ge=0.0, le=1.0)
    cursor:        str | None = None
    limit:         int = Field(default=20, ge=1, le=100)
```

---

## Report Schemas

```python
# app/domain/reports/schemas.py

class Citation(BaseModel):
    id:     int
    title:  str
    url:    str | None = None
    authors: list[str] = Field(default_factory=list)
    year:   int | None = None
    doi:    str | None = None

class ReportResponse(BaseModel, TimestampMixin):
    model_config = ConfigDict(from_attributes=True)
    id:                UUID
    job_id:            UUID
    project_id:        UUID
    title:             str
    status:            ReportStatus
    format:            ReportFormat
    executive_summary: str | None
    content:           str | None
    citations:         list[Citation]
    metadata:          dict[str, Any]
    quality_score:     Decimal | None
    word_count:        int | None
    version:           int
    is_published:      bool
    published_at:      datetime | None
    created_by:        UserSummary
    deleted_at:        datetime | None

class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:            UUID
    title:         str
    status:        ReportStatus
    quality_score: Decimal | None
    word_count:    int | None
    is_published:  bool
    created_at:    datetime

class FeedbackCreate(BaseModel):
    rating:  int = Field(ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)

class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:        UUID
    rating:    int
    comment:   str | None
    user:      UserSummary
    created_at: datetime
```

---

## Agent Log Schemas

```python
# app/domain/agent_logs/schemas.py

class AgentLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             UUID
    job_id:         UUID
    agent_type:     AgentType
    agent_instance: str | None
    parent_log_id:  UUID | None
    level:          LogLevel
    message:        str
    model_name:     str | None
    input_tokens:   int | None
    output_tokens:  int | None
    cost_usd:       Decimal | None
    latency_ms:     int | None
    tool_name:      str | None
    tool_input:     dict[str, Any] | None
    tool_output:    dict[str, Any] | None
    error_code:     str | None
    error_detail:   str | None
    trace_id:       str | None
    metadata:       dict[str, Any]
    created_at:     datetime

class LogFilter(BaseModel):
    agent_type: AgentType | None = None
    level:      LogLevel | None = None
    trace_id:   str | None = None
    since:      datetime | None = None
    cursor:     str | None = None
    limit:      int = Field(default=50, ge=1, le=200)

class LogStreamEvent(BaseModel):
    event:   Literal["agent_log", "job_status", "heartbeat"]
    data:    AgentLogResponse | JobSummary | dict
```

---

## Audit Log Schemas

```python
# app/domain/audit_logs/schemas.py

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:             UUID
    org_id:         UUID | None
    user:           UserSummary | None
    action:         AuditAction
    resource_type:  str
    resource_id:    UUID | None
    old_value:      dict[str, Any] | None
    new_value:      dict[str, Any] | None
    ip_address:     str | None
    request_id:     str | None
    result:         str
    failure_reason: str | None
    created_at:     datetime

class AuditFilter(BaseModel):
    user_id:       UUID | None = None
    action:        AuditAction | None = None
    resource_type: str | None = None
    resource_id:   UUID | None = None
    result:        Literal["success", "failure"] | None = None
    from_dt:       datetime | None = Field(None, alias="from")
    to_dt:         datetime | None = Field(None, alias="to")
    cursor:        str | None = None
    limit:         int = Field(default=50, ge=1, le=200)

    model_config = ConfigDict(populate_by_name=True)
```

---

## Enum Definitions

```python
# app/shared/enums.py

class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class ProjectVisibility(str, Enum):
    PRIVATE = "private"
    ORG = "org"
    PUBLIC = "public"

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class SourceType(str, Enum):
    WEB = "web"
    PDF = "pdf"
    DATABASE = "database"
    API = "api"
    MANUAL = "manual"
    VECTOR_STORE = "vector_store"

class SourceStatus(str, Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"
    EXCLUDED = "excluded"

class ReportStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

class ReportFormat(str, Enum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"

class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCH = "research"
    SYNTHESIS = "synthesis"
    CRITIQUE = "critique"
    FACTCHECK = "factcheck"
    MEMORY = "memory"
    CODE = "code"
    REPORT = "report"

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AuditAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    SHARE = "share"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"
```
