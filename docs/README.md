# Enterprise Multi-Agent AI Research Platform
## Architecture Documentation Index

## Phase 0 — Architecture Documentation

> **Principal AI Architect Design Document**
> Version: 1.0.0 | Status: Approved | Date: June 2026

---

## Platform Summary

A distributed, enterprise-grade Multi-Agent AI Research Platform that orchestrates 5 LLM models (GPT-4o, Claude Sonnet, Gemini 2.5 Pro, DeepSeek R1, Qwen 3) through a LangGraph-powered agent fleet to perform complex, multi-phase research workflows with full observability, security, and team-based module ownership.

---

## Technology Stack

| Layer | Technology |
|---|---|
| **API Backend** | FastAPI (Python 3.12, async) |
| **Frontend** | Next.js 15 (App Router, TypeScript) |
| **Orchestration** | LangGraph (stateful DAG workflows) |
| **Relational DB** | PostgreSQL 16 |
| **Cache / PubSub** | Redis 7 |
| **Vector DB** | Qdrant |
| **Containerization** | Docker + Docker Compose + Kubernetes |

---

## Documentation Index

| # | Document | Description |
|---|---|---|
| 01 | [High-Level Architecture](./architecture/01_high_level_architecture.md) | System context, component layers, architectural principles |
| 02 | [Multi-Agent Architecture](./architecture/02_multi_agent_architecture.md) | Agent taxonomy, LangGraph DAG, state schema, failure recovery |
| 03 | [Model Selection Strategy](./architecture/03_model_selection_strategy.md) | TMFS scoring, routing rules, failover table, cost management |
| 04 | [Agent Communication Workflow](./architecture/04_agent_communication_workflow.md) | Message protocol, Redis channels, end-to-end sequence, trust model |
| 05 | [Database Design](./architecture/05_database_design.md) | ERD, Redis structures, Qdrant collections, partitioning |
| 06 | [API Design](./architecture/06_api_design.md) | REST endpoints, WebSocket events, auth flow, rate limiting |
| 07 | [Security Architecture](./architecture/07_security_architecture.md) | Zero-trust, defense-in-depth, prompt injection defense, compliance |
| 08 | [Deployment Architecture](./architecture/08_deployment_architecture.md) | Docker Compose, Kubernetes, CI/CD, autoscaling, DR |
| 09 | [Folder Structure](./architecture/09_folder_structure.md) | Monorepo layout, module organization, structural decisions |
| 10 | [Team Module Separation](./architecture/10_team_module_separation.md) | 5-team ownership model, interfaces, SLOs, collaboration cadence |

---

## Quick Reference: Agent-to-Model Assignments

| Agent | Primary Model | Fallback Model |
|---|---|---|
| Orchestrator Agent | GPT-4o | Claude Sonnet |
| Research Agent | Gemini 2.5 Pro | Claude Sonnet |
| Synthesis Agent | Claude Sonnet | GPT-4o |
| Critique Agent | DeepSeek R1 | GPT-4o |
| Fact-Check Agent | Qwen 3 | DeepSeek R1 |
| Code Agent | DeepSeek R1 | GPT-4o |
| Report Agent | Claude Sonnet | GPT-4o |
| Memory Agent | GPT-4o | Gemini 2.5 Pro |

---

## Quick Reference: Team Ownership

| Team | Primary Domain | Key Modules |
|---|---|---|
| **Team 1 - Platform Core** | API, Auth, Infra | FastAPI gateway, JWT, RBAC, migrations |
| **Team 2 - AI Orchestration** | LangGraph, Routing | Graph DAGs, model router, checkpointer |
| **Team 3 - Agent Intelligence** | Agents, LLM Adapters | All 8 agents, 5 LLM adapters, tools |
| **Team 4 - Frontend & UX** | Next.js, Design | All pages, components, WebSocket client |
| **Team 5 - Data & ML Platform** | Vector DB, Memory | Qdrant, embeddings, semantic search |

---

## Architecture Decision Records (ADRs)

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | Use LangGraph over custom orchestration | Accepted |
| ADR-002 | Qdrant over pgvector for vector storage | Accepted |
| ADR-003 | RS256 JWT with Redis-backed refresh token revocation | Accepted |
| ADR-004 | Redis Pub/Sub for agent communication (not Kafka) | Accepted |
| ADR-005 | Monorepo structure with independent service builds | Accepted |
| ADR-006 | PostgreSQL checkpointer for LangGraph state persistence | Accepted |
