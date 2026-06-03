# Backend Architecture — API Specification

> **Base URL**: `https://api.yourplatform.com/api/v1`
> **Authentication**: `Authorization: Bearer <access_token>` (JWT RS256)
> **Content-Type**: `application/json`
> **All timestamps**: ISO 8601 UTC (`2026-06-03T13:00:00Z`)

---

## Standard Response Envelopes

### Success
```json
{
  "status": "success",
  "data": { },
  "meta": { "total": 100, "next_cursor": "eyJpZCI6...", "page_size": 20 },
  "trace_id": "01HXYZ...",
  "timestamp": "2026-06-03T13:00:00Z"
}
```

### Error
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "field_errors": { "email": ["Invalid email format"] },
    "doc_url": "https://docs.yourplatform.com/errors/VALIDATION_ERROR"
  },
  "trace_id": "01HXYZ...",
  "timestamp": "2026-06-03T13:00:00Z"
}
```

---

## Error Codes

| HTTP | Code | Description |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body/query param failed Pydantic validation |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 401 | `TOKEN_EXPIRED` | JWT has expired |
| 403 | `FORBIDDEN` | Authenticated but insufficient permissions |
| 404 | `NOT_FOUND` | Resource does not exist or is soft-deleted |
| 409 | `CONFLICT` | Unique constraint violation (e.g., duplicate email) |
| 422 | `UNPROCESSABLE_ENTITY` | Business rule violation |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `SERVICE_UNAVAILABLE` | DB or Redis unreachable |

---

## Authentication Endpoints

### `POST /auth/register`
Register a new user and organization.

**Request**
```json
{
  "org_name": "Acme Research Labs",
  "email": "alice@acme.com",
  "username": "alice",
  "full_name": "Alice Chen",
  "password": "S3cure!Pass#2026"
}
```

**Response** `201 Created`
```json
{
  "status": "success",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "alice@acme.com",
    "message": "Verification email sent"
  }
}
```

---

### `POST /auth/login`
Authenticate and receive token pair.

**Request**
```json
{ "email": "alice@acme.com", "password": "S3cure!Pass#2026" }
```

**Response** `200 OK`
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJSUzI1NiJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

---

### `POST /auth/refresh`
Rotate access token using refresh token.

**Request**
```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiJ9..." }
```

**Response** `200 OK` — Same shape as login response.

---

### `POST /auth/logout`
Revoke refresh token (adds to Redis blocklist).

**Response** `204 No Content`

---

## User Endpoints

### `GET /users/me`
Get the authenticated user's profile.

**Response** `200 OK`
```json
{
  "data": {
    "id": "550e8400-...",
    "email": "alice@acme.com",
    "username": "alice",
    "full_name": "Alice Chen",
    "role": "researcher",
    "status": "active",
    "org_id": "org-uuid",
    "preferences": {},
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

---

### `PATCH /users/me`
Update own profile.

**Request**
```json
{
  "full_name": "Alice Chen-Wei",
  "preferences": { "theme": "dark", "email_notifications": true }
}
```

---

### `POST /users/me/api-keys`
Create an API key.

**Request**
```json
{ "name": "CI Pipeline Key", "scopes": ["read:jobs", "write:jobs"], "expires_at": "2027-01-01T00:00:00Z" }
```

**Response** `201 Created`
```json
{
  "data": {
    "id": "key-uuid",
    "name": "CI Pipeline Key",
    "key": "ma_live_sk_abc123xyz...",
    "key_prefix": "ma_live_",
    "scopes": ["read:jobs", "write:jobs"],
    "expires_at": "2027-01-01T00:00:00Z",
    "created_at": "2026-06-03T13:00:00Z"
  },
  "meta": { "warning": "This key is shown only once. Store it securely." }
}
```

---

### `GET /users` _(admin only)_
List all users in the organization.

**Query Parameters**
| Param | Type | Default | Description |
|---|---|---|---|
| `cursor` | string | — | Pagination cursor |
| `limit` | int | 20 | Max 100 |
| `status` | enum | — | Filter by status |
| `role` | enum | — | Filter by role |
| `search` | string | — | Search by name/email |

---

### `GET /users/{user_id}` _(admin only)_
### `PATCH /users/{user_id}` _(admin only)_
### `DELETE /users/{user_id}` _(admin: soft delete)_

---

## Project Endpoints

### `POST /projects`
Create a new research project.

**Request**
```json
{
  "title": "Q3 2026 AI Safety Research",
  "description": "Investigating alignment risks in frontier models",
  "visibility": "org",
  "tags": ["ai-safety", "alignment", "frontier-models"],
  "settings": {
    "max_jobs": 50,
    "default_model": "gemini-2.5-pro",
    "quality_threshold": 0.85
  }
}
```

**Response** `201 Created`
```json
{
  "data": {
    "id": "proj-uuid",
    "title": "Q3 2026 AI Safety Research",
    "slug": "q3-2026-ai-safety-research",
    "status": "draft",
    "visibility": "org",
    "tags": ["ai-safety", "alignment"],
    "job_count": 0,
    "owner": { "id": "user-uuid", "full_name": "Alice Chen" },
    "created_at": "2026-06-03T13:00:00Z"
  }
}
```

---

### `GET /projects`
List projects visible to the current user.

**Query Parameters**
| Param | Type | Description |
|---|---|---|
| `cursor` | string | Pagination cursor |
| `limit` | int | Default 20, max 50 |
| `status` | enum | draft, active, completed, archived |
| `tags` | string[] | Filter by tags (AND logic) |
| `search` | string | Full-text search on title |

---

### `GET /projects/{project_id}`
### `PATCH /projects/{project_id}`
### `DELETE /projects/{project_id}` _(soft delete)_

---

### `POST /projects/{project_id}/members`
Invite a user to a project.

**Request**
```json
{ "user_id": "user-uuid", "role": "editor" }
```

### `DELETE /projects/{project_id}/members/{user_id}`
Remove a project member.

---

## Research Job Endpoints

### `POST /projects/{project_id}/jobs`
Create and queue a research job.

**Request**
```json
{
  "title": "Comparative analysis of RLHF vs RLAIF",
  "query": "Compare Reinforcement Learning from Human Feedback vs AI Feedback approaches for frontier model alignment. Include recent 2024–2026 papers.",
  "priority": "high",
  "config": {
    "enabled_agents": ["research", "factcheck", "synthesis", "critique", "report"],
    "model_preferences": {
      "research": "gemini-2.5-pro",
      "synthesis": "claude-sonnet",
      "critique": "deepseek-r1"
    },
    "max_tokens_budget": 200000,
    "quality_threshold": 0.88,
    "enable_code_execution": false,
    "output_format": "markdown",
    "timeout_seconds": 600
  },
  "scheduled_at": null
}
```

**Response** `202 Accepted`
```json
{
  "data": {
    "id": "job-uuid",
    "title": "Comparative analysis of RLHF vs RLAIF",
    "status": "queued",
    "priority": "high",
    "progress_percent": 0,
    "ws_url": "wss://api.yourplatform.com/ws/jobs/job-uuid",
    "created_at": "2026-06-03T13:00:00Z"
  }
}
```

---

### `GET /projects/{project_id}/jobs`
List all jobs in a project.

**Query Parameters**
| Param | Type | Description |
|---|---|---|
| `cursor` | string | Pagination cursor |
| `limit` | int | Default 20 |
| `status` | enum | queued, running, completed, failed, cancelled |
| `priority` | enum | low, normal, high, critical |
| `sort` | string | `created_at_desc` (default), `created_at_asc` |

---

### `GET /jobs/{job_id}`
Get full job detail including orchestration plan and progress.

**Response** `200 OK`
```json
{
  "data": {
    "id": "job-uuid",
    "title": "Comparative analysis of RLHF vs RLAIF",
    "query": "...",
    "status": "running",
    "priority": "high",
    "progress_percent": 45,
    "quality_score": null,
    "total_tokens_used": 42500,
    "total_cost_usd": "0.183200",
    "config": { },
    "orchestration_plan": {
      "subtasks": ["retrieve-rlhf-papers", "retrieve-rlaif-papers", "compare-methods"],
      "agent_assignments": { }
    },
    "retry_count": 0,
    "started_at": "2026-06-03T13:01:00Z",
    "completed_at": null,
    "created_at": "2026-06-03T13:00:00Z"
  }
}
```

---

### `POST /jobs/{job_id}/cancel`
Cancel a running or queued job.

**Request** `{}` (empty body)
**Response** `200 OK` with updated job status.

---

### `POST /jobs/{job_id}/retry`
Retry a failed job (respects `max_retries`).

---

## Source Endpoints

### `GET /jobs/{job_id}/sources`
List all sources collected by a job.

**Query Parameters**
| Param | Type | Description |
|---|---|---|
| `cursor` | string | Pagination cursor |
| `limit` | int | Default 20 |
| `type` | enum | web, pdf, database, api, manual |
| `status` | enum | pending, indexed, failed, excluded |
| `min_relevance` | float | Filter by minimum relevance score |

**Response** `200 OK`
```json
{
  "data": [
    {
      "id": "src-uuid",
      "source_type": "web",
      "status": "indexed",
      "title": "Constitutional AI: Harmlessness from AI Feedback",
      "url": "https://arxiv.org/abs/2212.08073",
      "relevance_score": 0.947,
      "chunk_count": 12,
      "content_preview": "We explore a method for training a harmless AI assistant...",
      "indexed_at": "2026-06-03T13:02:00Z",
      "created_at": "2026-06-03T13:01:30Z"
    }
  ],
  "meta": { "total": 34, "next_cursor": null }
}
```

---

### `DELETE /jobs/{job_id}/sources/{source_id}`
Exclude a source from a job's context.

---

## Report Endpoints

### `GET /jobs/{job_id}/reports`
List reports generated for a job.

### `GET /reports/{report_id}`
Get full report content.

**Response** `200 OK`
```json
{
  "data": {
    "id": "rpt-uuid",
    "title": "RLHF vs RLAIF: Comparative Analysis",
    "status": "completed",
    "format": "markdown",
    "executive_summary": "This report examines...",
    "content": "# RLHF vs RLAIF\n\n## Introduction\n...",
    "citations": [
      { "id": 1, "title": "Constitutional AI", "url": "...", "year": 2022 }
    ],
    "quality_score": 0.912,
    "word_count": 3847,
    "version": 1,
    "is_published": false,
    "created_at": "2026-06-03T13:10:00Z"
  }
}
```

---

### `GET /reports/{report_id}/export`
Download report as PDF or HTML.

**Query Parameters**: `format=pdf|html|markdown`

**Response**: Binary file stream with appropriate Content-Type.

---

### `POST /reports/{report_id}/feedback`
Submit quality feedback for a report.

**Request**
```json
{ "rating": 4, "comment": "Well-structured but missing coverage of PPO vs DPO comparison." }
```

**Response** `201 Created`

---

### `POST /reports/{report_id}/publish`
Publish a report (make visible based on project visibility settings).

---

## Agent Logs Endpoints

### `GET /jobs/{job_id}/logs`
Retrieve paginated agent execution logs for a job.

**Query Parameters**
| Param | Type | Description |
|---|---|---|
| `cursor` | string | Pagination cursor |
| `limit` | int | Default 50, max 200 |
| `agent_type` | enum | Filter by agent type |
| `level` | enum | debug, info, warning, error, critical |
| `trace_id` | string | Filter by distributed trace |
| `since` | datetime | Return logs after this timestamp |

**Response** `200 OK`
```json
{
  "data": [
    {
      "id": "log-uuid",
      "agent_type": "research",
      "agent_instance": "research-01-abc123",
      "level": "info",
      "message": "Retrieved 12 papers from ArXiv search",
      "model_name": "gemini-2.5-pro",
      "input_tokens": 1024,
      "output_tokens": 3840,
      "cost_usd": "0.012300",
      "latency_ms": 4230,
      "tool_name": "web_search",
      "tool_input": { "query": "RLAIF constitutional AI 2024" },
      "tool_output": { "results_count": 12 },
      "trace_id": "01HXYZ...",
      "created_at": "2026-06-03T13:01:45Z"
    }
  ],
  "meta": { "total": 287, "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNi0wNi0wM1QxMzowMTo0NVoifQ==" }
}
```

---

### `GET /jobs/{job_id}/logs/stream`
Server-Sent Events stream for real-time log tailing during job execution.

**Response**: `text/event-stream`
```
event: agent_log
data: {"agent_type":"synthesis","level":"info","message":"Merging 34 source chunks...","created_at":"..."}

event: job_status
data: {"status":"completed","progress_percent":100,"quality_score":0.912}
```

---

## Audit Log Endpoints _(admin only)_

### `GET /audit-logs`
Query audit trail with rich filtering.

**Query Parameters**
| Param | Type | Description |
|---|---|---|
| `cursor` | string | Pagination cursor |
| `limit` | int | Default 50, max 200 |
| `user_id` | uuid | Filter by actor |
| `action` | enum | Filter by action type |
| `resource_type` | string | Filter by resource (user, project, report…) |
| `resource_id` | uuid | Filter by specific resource |
| `result` | string | success, failure |
| `from` | datetime | Range start |
| `to` | datetime | Range end |

**Response** `200 OK`
```json
{
  "data": [
    {
      "id": "audit-uuid",
      "user": { "id": "user-uuid", "email": "alice@acme.com" },
      "action": "delete",
      "resource_type": "report",
      "resource_id": "rpt-uuid",
      "old_value": { "title": "Draft Report", "status": "draft" },
      "new_value": null,
      "ip_address": "192.168.1.100",
      "result": "success",
      "created_at": "2026-06-03T13:15:00Z"
    }
  ],
  "meta": { "total": 1523, "next_cursor": "..." }
}
```

---

## Health Check Endpoints _(no auth required)_

### `GET /health`
Basic liveness probe.
```json
{ "status": "ok", "version": "1.3.2", "timestamp": "2026-06-03T13:00:00Z" }
```

### `GET /health/ready`
Readiness probe — checks DB and Redis connectivity.
```json
{
  "status": "ready",
  "checks": {
    "database": { "status": "ok", "latency_ms": 2 },
    "redis": { "status": "ok", "latency_ms": 1 }
  }
}
```

---

## Rate Limit Headers

All responses include:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1717416000
Retry-After: 30              (only on 429)
```

---

## Idempotency

`POST` endpoints that create resources accept an optional idempotency key:
```
Idempotency-Key: <uuid-v4>
```
Duplicate requests with the same key within 24 hours return the original response without re-executing.
