# 1. High-Level Architecture

## Overview

The **Enterprise Multi-Agent AI Research Platform** is a distributed, microservices-based system designed to orchestrate multiple large language models (LLMs) for complex research workflows. It enables parallel model execution, intelligent task routing, result synthesis, and persistent memory across sessions.

---

## Architectural Principles

| Principle | Description |
|---|---|
| **Model Agnosticism** | Agents are decoupled from specific LLM providers via a unified adapter layer |
| **Event-Driven Orchestration** | LangGraph manages stateful agent workflows via directed acyclic graphs (DAGs) |
| **Separation of Concerns** | Each layer (API, Agent, Storage, UI) has independent scaling and deployment |
| **Defense-in-Depth Security** | Multi-layer security: API Gateway → Auth → Network → Data encryption |
| **Observability-First** | Every agent action, LLM call, and data flow is traced, logged, and metered |

---

## System Context Diagram

```mermaid
C4Context
    title System Context — Multi-Agent AI Research Platform

    Person(researcher, "Researcher", "Submits research queries, reviews synthesized outputs")
    Person(admin, "Platform Admin", "Manages models, agents, users, and system health")

    System_Boundary(platform, "Multi-Agent AI Research Platform") {
        System(frontend, "Next.js 15 Web App", "Research dashboard and agent visualization UI")
        System(api, "FastAPI Gateway", "Orchestration, auth, and agent coordination")
        System(agents, "Agent Cluster", "Specialized LangGraph agent fleet")
        System(memory, "Memory & Vector Layer", "Qdrant + Redis for semantic search and caching")
        System(storage, "Persistent Storage", "PostgreSQL for audit, sessions, and results")
    }

    System_Ext(openai, "OpenAI API", "GPT-4o")
    System_Ext(anthropic, "Anthropic API", "Claude Sonnet")
    System_Ext(google, "Google AI API", "Gemini 2.5 Pro")
    System_Ext(deepseek, "DeepSeek API", "DeepSeek R1")
    System_Ext(alibaba, "Alibaba Cloud API", "Qwen 3")

    Rel(researcher, frontend, "Uses HTTPS")
    Rel(admin, frontend, "Manages via")
    Rel(frontend, api, "REST / WebSocket")
    Rel(api, agents, "Dispatches tasks")
    Rel(agents, memory, "Reads/writes context")
    Rel(agents, storage, "Persists results")
    Rel(agents, openai, "LLM calls")
    Rel(agents, anthropic, "LLM calls")
    Rel(agents, google, "LLM calls")
    Rel(agents, deepseek, "LLM calls")
    Rel(agents, alibaba, "LLM calls")
```

---

## High-Level Component Architecture

```mermaid
flowchart TB
    subgraph ClientLayer["Client Layer"]
        UI["Next.js 15\nResearch Dashboard"]
        WS["WebSocket\nReal-time Updates"]
    end

    subgraph GatewayLayer["API Gateway Layer"]
        APIGW["FastAPI\nAPI Gateway"]
        AUTH["Auth Service\nJWT / OAuth2"]
        RATELIM["Rate Limiter\n(Redis-backed)"]
        LB["Load Balancer\nNginx / Traefik"]
    end

    subgraph OrchestrationLayer["Orchestration Layer"]
        ORCH["LangGraph\nOrchestrator"]
        ROUTER["Model Router\nSelection Engine"]
        TASKMGR["Task Manager\nQueue & Priority"]
    end

    subgraph AgentLayer["Agent Fleet"]
        RA["Research Agent"]
        SA["Synthesis Agent"]
        FA["Fact-Check Agent"]
        CA["Critique Agent"]
        MA["Memory Agent"]
    end

    subgraph ModelLayer["LLM Provider Layer"]
        GPT4O["GPT-4o\nOpenAI"]
        CLAUDE["Claude Sonnet\nAnthropic"]
        GEMINI["Gemini 2.5 Pro\nGoogle"]
        DEEPSEEK["DeepSeek R1\nDeepSeek"]
        QWEN["Qwen 3\nAlibaba"]
    end

    subgraph StorageLayer["Storage Layer"]
        PG["PostgreSQL\nRelational DB"]
        REDIS["Redis\nCache & Pub/Sub"]
        QDRANT["Qdrant\nVector Store"]
        S3["Object Storage\nFiles & Artifacts"]
    end

    subgraph ObservabilityLayer["Observability"]
        PROM["Prometheus\nMetrics"]
        GRAF["Grafana\nDashboards"]
        LOKI["Loki\nLogs"]
        OTEL["OpenTelemetry\nTracing"]
    end

    UI <--> LB
    WS <--> LB
    LB --> APIGW
    APIGW --> AUTH
    APIGW --> RATELIM
    APIGW --> ORCH
    ORCH --> ROUTER
    ORCH --> TASKMGR
    TASKMGR --> RA
    TASKMGR --> SA
    TASKMGR --> FA
    TASKMGR --> CA
    TASKMGR --> MA
    ROUTER --> GPT4O
    ROUTER --> CLAUDE
    ROUTER --> GEMINI
    ROUTER --> DEEPSEEK
    ROUTER --> QWEN
    RA & SA & FA & CA & MA --> REDIS
    RA & SA & FA & CA & MA --> QDRANT
    RA & SA & FA & CA & MA --> PG
    APIGW --> OTEL
    ORCH --> OTEL
    OTEL --> PROM
    PROM --> GRAF
    OTEL --> LOKI
```

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **API Framework** | FastAPI | Async-first, OpenAPI auto-docs, Pydantic validation |
| **Orchestration** | LangGraph | Stateful DAGs, cyclical agent loops, built-in checkpointing |
| **Frontend** | Next.js 15 | App Router, Server Components, streaming SSE support |
| **Vector DB** | Qdrant | High-performance ANN search, filterable payloads, gRPC support |
| **Cache/PubSub** | Redis | Session cache, rate limiting, agent pub/sub messaging |
| **Relational DB** | PostgreSQL | ACID compliance, JSONB for flexible schema, pgvector if needed |
| **Containerization** | Docker + Compose | Reproducible environments, isolated services |
