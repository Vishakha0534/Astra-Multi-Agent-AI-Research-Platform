# Backend Architecture — Index
## Phase 1 — Backend Core Setup
> **Senior Backend Architect Design Document**
> Stack: FastAPI · PostgreSQL · Redis · SQLAlchemy 2.0 (async) · Alembic
> Version: 1.0.0 | Status: Approved

---

## Documentation Index

| # | Document | Description |
|---|---|---|
| 01 | [Database Schema & ER Diagram](./01_database_schema.md) | SQL DDL, enum types, indexes, RLS policies, triggers, full ER diagram |
| 02 | [Folder Structure](./02_folder_structure.md) | Monorepo layout, module dependency rules, hexagonal architecture |
| 03 | [API Specification](./03_api_specification.md) | All REST endpoints, request/response examples, rate limiting, idempotency |
| 04 | [Request/Response Schemas](./04_request_response_schemas.md) | Pydantic v2 schemas, enum definitions, base models |
| 05 | [Domain Services Design](./05_domain_services.md) | Service contracts, UML class diagrams, state machines, Redis usage |
| 06 | [Infrastructure Design](./06_infrastructure_design.md) | SQLAlchemy config, Alembic strategy, Redis keys, DI wiring, exceptions |

---

## Tables Summary

| Table | Rows/Day (est.) | Partitioned | RLS |
|---|---|---|---|
| `organizations` | < 10 | No | No |
| `users` | < 100 | No | No |
| `api_keys` | < 50 | No | No |
| `projects` | < 200 | No | ✅ |
| `project_members` | < 500 | No | No |
| `research_jobs` | 1K–10K | ✅ Monthly | ✅ |
| `sources` | 10K–100K | No | ✅ |
| `reports` | 1K–10K | No | ✅ |
| `report_feedback` | < 1K | No | No |
| `agent_logs` | 100K–1M | ✅ Weekly | No |
| `audit_logs` | 10K–100K | ✅ Quarterly | No |

---

## API Surface Summary

| Domain | Endpoints | Auth Required |
|---|---|---|
| Auth | POST /register, /login, /refresh, /logout | Partial |
| Users | GET/PATCH /users/me, GET/PATCH/DELETE /users/{id} | ✅ |
| API Keys | POST/GET/DELETE /users/me/api-keys | ✅ |
| Organizations | GET/PATCH /organizations | ✅ |
| Projects | Full CRUD + members | ✅ |
| Research Jobs | Full CRUD + cancel + retry | ✅ |
| Sources | GET/DELETE /jobs/{id}/sources | ✅ |
| Reports | Full CRUD + export + publish + feedback | ✅ |
| Agent Logs | GET + stream (SSE) | ✅ |
| Audit Logs | GET (admin only) | ✅ Admin |
| Health | /health, /health/ready | ❌ |

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| ORM | SQLAlchemy 2.0 async (mapped_column) | Type-safe, async-native, production-proven |
| Async driver | `asyncpg` | Fastest PostgreSQL async driver |
| Validation | Pydantic v2 | 5–50x faster than v1, Rust core |
| Auth | RS256 JWT + Redis refresh revocation | Stateless verify + server-side invalidate |
| Pagination | Cursor-based | O(1) regardless of offset depth |
| Soft deletes | `deleted_at` column | Audit trail, recoverability, referential integrity |
| Audit writes | Separate session | Audit commits independently from business transaction |
| Log partitioning | `agent_logs` weekly, `audit_logs` quarterly | Manageability + retention policy enforcement |
| Rate limiting | Redis sliding window (token bucket) | Accurate, distributed-safe |
| Config | `pydantic-settings` + env vars | 12-Factor app compliance |
