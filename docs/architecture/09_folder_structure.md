# 9. Folder Structure

## Design Principles

- **Monorepo**: All services in one repository for atomic commits and shared tooling
- **Domain-Driven Organization**: Directories named after business domains, not technical layers
- **Strict Module Boundaries**: Each service is independently buildable and deployable
- **Shared Packages**: Common utilities (types, schemas, utils) in a shared workspace package

---

## Complete Repository Structure

```
multi-agent-research-platform/
│
├── 📄 README.md
├── 📄 docker-compose.yml           # Dev environment orchestration
├── 📄 docker-compose.prod.yml      # Production overrides
├── 📄 Makefile                     # Developer shortcuts
├── 📄 .env.example                 # Environment variable template
├── 📄 .gitignore
├── 📄 .dockerignore
│
├── 📁 docs/                        # All architecture & design documentation
│   ├── 📁 architecture/
│   │   ├── 01_high_level_architecture.md
│   │   ├── 02_multi_agent_architecture.md
│   │   ├── 03_model_selection_strategy.md
│   │   ├── 04_agent_communication_workflow.md
│   │   ├── 05_database_design.md
│   │   ├── 06_api_design.md
│   │   ├── 07_security_architecture.md
│   │   ├── 08_deployment_architecture.md
│   │   ├── 09_folder_structure.md
│   │   └── 10_team_module_separation.md
│   ├── 📁 adr/                     # Architecture Decision Records
│   │   ├── 001-use-langgraph.md
│   │   ├── 002-qdrant-vs-pgvector.md
│   │   └── 003-jwt-auth-strategy.md
│   └── 📁 runbooks/                # Operational runbooks
│       ├── incident-response.md
│       └── deployment-checklist.md
│
├── 📁 backend/                     # FastAPI backend service
│   ├── 📄 Dockerfile
│   ├── 📄 pyproject.toml           # Poetry config + dependencies
│   ├── 📄 alembic.ini              # Database migration config
│   │
│   ├── 📁 app/
│   │   ├── 📄 main.py              # FastAPI app factory
│   │   ├── 📄 config.py            # Settings via pydantic-settings
│   │   ├── 📄 dependencies.py      # FastAPI DI: DB, Redis, Auth
│   │   │
│   │   ├── 📁 api/                 # Route definitions
│   │   │   ├── 📄 router.py        # Root API router
│   │   │   ├── 📁 v1/
│   │   │   │   ├── 📄 auth.py
│   │   │   │   ├── 📄 users.py
│   │   │   │   ├── 📄 organizations.py
│   │   │   │   ├── 📄 research_sessions.py
│   │   │   │   ├── 📄 research_reports.py
│   │   │   │   ├── 📄 knowledge.py
│   │   │   │   ├── 📄 models.py
│   │   │   │   └── 📄 health.py
│   │   │   └── 📁 ws/
│   │   │       ├── 📄 session_ws.py    # WebSocket for session events
│   │   │       └── 📄 agent_ws.py     # WebSocket for agent monitoring
│   │   │
│   │   ├── 📁 core/                # Cross-cutting concerns
│   │   │   ├── 📄 security.py      # JWT encode/decode, password hash
│   │   │   ├── 📄 rate_limiter.py  # Redis sliding-window rate limiter
│   │   │   ├── 📄 exceptions.py    # Custom exception classes
│   │   │   ├── 📄 middleware.py    # Logging, tracing, CORS middleware
│   │   │   └── 📄 events.py        # App startup/shutdown handlers
│   │   │
│   │   ├── 📁 domain/              # Business domain modules
│   │   │   ├── 📁 auth/
│   │   │   │   ├── 📄 schemas.py
│   │   │   │   ├── 📄 service.py
│   │   │   │   └── 📄 models.py
│   │   │   ├── 📁 research/
│   │   │   │   ├── 📄 schemas.py
│   │   │   │   ├── 📄 service.py
│   │   │   │   └── 📄 models.py
│   │   │   ├── 📁 knowledge/
│   │   │   │   ├── 📄 schemas.py
│   │   │   │   ├── 📄 service.py
│   │   │   │   └── 📄 models.py
│   │   │   └── 📁 users/
│   │   │       ├── 📄 schemas.py
│   │   │       ├── 📄 service.py
│   │   │       └── 📄 models.py
│   │   │
│   │   └── 📁 infrastructure/      # External adapter implementations
│   │       ├── 📁 database/
│   │       │   ├── 📄 session.py   # SQLAlchemy async session
│   │       │   └── 📄 base.py      # Declarative base
│   │       ├── 📁 cache/
│   │       │   └── 📄 redis.py     # Redis client factory
│   │       └── 📁 messaging/
│   │           └── 📄 pubsub.py    # Redis pub/sub client
│   │
│   ├── 📁 alembic/                 # Database migrations
│   │   ├── 📄 env.py
│   │   └── 📁 versions/
│   │
│   └── 📁 tests/
│       ├── 📄 conftest.py
│       ├── 📁 unit/
│       └── 📁 integration/
│
├── 📁 orchestrator/                # LangGraph orchestration service
│   ├── 📄 Dockerfile
│   ├── 📄 pyproject.toml
│   │
│   ├── 📁 orchestrator/
│   │   ├── 📄 main.py              # Orchestrator service entry
│   │   ├── 📄 config.py
│   │   │
│   │   ├── 📁 graphs/              # LangGraph workflow definitions
│   │   │   ├── 📄 research_graph.py    # Main research DAG
│   │   │   ├── 📄 revision_graph.py    # Revision loop sub-graph
│   │   │   └── 📄 base_graph.py        # Graph builder utilities
│   │   │
│   │   ├── 📁 nodes/               # LangGraph node implementations
│   │   │   ├── 📄 intake_node.py
│   │   │   ├── 📄 decompose_node.py
│   │   │   ├── 📄 quality_gate_node.py
│   │   │   └── 📄 completion_node.py
│   │   │
│   │   ├── 📁 state/               # LangGraph state schemas
│   │   │   ├── 📄 research_state.py
│   │   │   └── 📄 task_state.py
│   │   │
│   │   ├── 📁 checkpointers/       # State persistence
│   │   │   └── 📄 postgres_checkpointer.py
│   │   │
│   │   └── 📁 router/              # Model selection engine
│   │       ├── 📄 model_router.py
│   │       ├── 📄 scoring.py
│   │       └── 📄 failover.py
│   │
│   └── 📁 tests/
│
├── 📁 agents/                      # Agent worker service
│   ├── 📄 Dockerfile
│   ├── 📄 pyproject.toml
│   │
│   ├── 📁 agents/
│   │   ├── 📄 main.py              # Agent worker entry (consumes from Redis)
│   │   ├── 📄 config.py
│   │   ├── 📄 base_agent.py        # Abstract base agent class
│   │   │
│   │   ├── 📁 implementations/     # Concrete agent implementations
│   │   │   ├── 📄 research_agent.py
│   │   │   ├── 📄 synthesis_agent.py
│   │   │   ├── 📄 critique_agent.py
│   │   │   ├── 📄 factcheck_agent.py
│   │   │   ├── 📄 memory_agent.py
│   │   │   ├── 📄 code_agent.py
│   │   │   └── 📄 report_agent.py
│   │   │
│   │   ├── 📁 tools/               # LangChain-compatible tools
│   │   │   ├── 📄 web_search.py
│   │   │   ├── 📄 document_loader.py
│   │   │   ├── 📄 vector_search.py
│   │   │   ├── 📄 code_executor.py
│   │   │   └── 📄 citation_formatter.py
│   │   │
│   │   ├── 📁 llm_adapters/        # Unified LLM provider adapters
│   │   │   ├── 📄 base.py          # Abstract LLM adapter
│   │   │   ├── 📄 openai_adapter.py
│   │   │   ├── 📄 anthropic_adapter.py
│   │   │   ├── 📄 gemini_adapter.py
│   │   │   ├── 📄 deepseek_adapter.py
│   │   │   └── 📄 qwen_adapter.py
│   │   │
│   │   └── 📁 memory/              # Memory management
│   │       ├── 📄 context_manager.py
│   │       ├── 📄 embedder.py
│   │       └── 📄 qdrant_client.py
│   │
│   └── 📁 tests/
│
├── 📁 frontend/                    # Next.js 15 application
│   ├── 📄 Dockerfile
│   ├── 📄 package.json
│   ├── 📄 next.config.ts
│   ├── 📄 tsconfig.json
│   ├── 📄 tailwind.config.ts       # Only if Tailwind used
│   │
│   ├── 📁 app/                     # Next.js 15 App Router
│   │   ├── 📄 layout.tsx
│   │   ├── 📄 page.tsx             # Landing / redirect
│   │   ├── 📁 (auth)/
│   │   │   ├── 📁 login/
│   │   │   └── 📁 register/
│   │   ├── 📁 (dashboard)/
│   │   │   ├── 📄 layout.tsx
│   │   │   ├── 📁 research/
│   │   │   │   ├── 📄 page.tsx     # Session list
│   │   │   │   ├── 📁 new/         # Create session
│   │   │   │   └── 📁 [id]/        # Session detail + live view
│   │   │   ├── 📁 reports/
│   │   │   ├── 📁 knowledge/
│   │   │   ├── 📁 models/
│   │   │   └── 📁 settings/
│   │   └── 📁 api/                 # Next.js API routes (BFF layer)
│   │       └── 📁 auth/
│   │
│   ├── 📁 components/              # Reusable UI components
│   │   ├── 📁 ui/                  # Primitive components (Button, Input, etc.)
│   │   ├── 📁 research/            # Research-domain components
│   │   ├── 📁 agents/              # Agent monitor components
│   │   ├── 📁 charts/              # Data visualization
│   │   └── 📁 layout/              # Shell, sidebar, nav
│   │
│   ├── 📁 lib/                     # Utilities and API client
│   │   ├── 📄 api-client.ts        # Type-safe API client
│   │   ├── 📄 ws-client.ts         # WebSocket client
│   │   ├── 📄 auth.ts              # Auth helpers
│   │   └── 📄 utils.ts
│   │
│   ├── 📁 hooks/                   # Custom React hooks
│   │   ├── 📄 use-session.ts
│   │   ├── 📄 use-ws.ts
│   │   └── 📄 use-agents.ts
│   │
│   ├── 📁 stores/                  # Zustand state stores
│   │   ├── 📄 session-store.ts
│   │   └── 📄 auth-store.ts
│   │
│   └── 📁 types/                   # TypeScript type definitions
│       ├── 📄 api.ts
│       ├── 📄 agents.ts
│       └── 📄 models.ts
│
├── 📁 infra/                       # Infrastructure as Code
│   ├── 📁 docker/
│   │   ├── 📄 nginx.conf
│   │   └── 📁 certs/
│   ├── 📁 k8s/                     # Kubernetes manifests
│   │   ├── 📁 base/
│   │   │   ├── 📁 backend/
│   │   │   ├── 📁 orchestrator/
│   │   │   ├── 📁 agents/
│   │   │   ├── 📁 frontend/
│   │   │   ├── 📁 postgres/
│   │   │   ├── 📁 redis/
│   │   │   └── 📁 qdrant/
│   │   └── 📁 overlays/
│   │       ├── 📁 staging/
│   │       └── 📁 production/
│   ├── 📁 helm/                    # Helm chart (optional)
│   └── 📁 monitoring/
│       ├── 📄 prometheus.yml
│       ├── 📁 grafana-dashboards/
│       └── 📄 alertmanager.yml
│
├── 📁 shared/                      # Shared Python utilities (monorepo package)
│   ├── 📄 pyproject.toml
│   └── 📁 shared/
│       ├── 📄 schemas.py           # Pydantic models shared across services
│       ├── 📄 enums.py             # Shared enumerations
│       ├── 📄 logging.py           # Structured logging config
│       └── 📄 tracing.py          # OpenTelemetry setup
│
└── 📁 .github/                     # GitHub Actions CI/CD
    ├── 📁 workflows/
    │   ├── 📄 ci.yml
    │   ├── 📄 deploy-staging.yml
    │   └── 📄 deploy-production.yml
    └── 📁 ISSUE_TEMPLATE/
```

---

## Key Structural Decisions

| Decision | Rationale |
|---|---|
| **Separate `orchestrator/` service** | Decouples workflow state from HTTP serving; scales independently |
| **Separate `agents/` service** | Worker replicas scale by queue depth; isolated from API latency |
| **`shared/` package** | Prevents schema duplication across Python services |
| **`llm_adapters/` pattern** | Swap or add new LLM providers without touching agent logic |
| **`tools/` directory in agents** | LangChain-compatible tool set; reusable across all agents |
| **`domain/` in backend** | Enforces hexagonal architecture; service layer isolated from HTTP |
| **App Router in Next.js** | Server Components reduce JS bundle; streaming support for SSE |
