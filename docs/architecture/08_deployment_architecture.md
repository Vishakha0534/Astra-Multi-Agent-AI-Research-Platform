# 8. Deployment Architecture

## Deployment Philosophy

- **Container-First**: Every service runs in Docker containers
- **Infrastructure as Code**: All infrastructure defined via Docker Compose (dev) and Kubernetes manifests (production)
- **Immutable Deployments**: No in-place mutations; blue/green and canary releases
- **GitOps**: All deployments triggered by Git commits via CI/CD pipeline
- **12-Factor App Compliance**: Configuration via environment, stateless services, disposable containers

---

## Environment Tiers

| Environment | Infrastructure | Purpose |
|---|---|---|
| **Local Dev** | Docker Compose | Developer workstation, all services local |
| **CI** | GitHub Actions + Docker | Automated testing, lint, type-check |
| **Staging** | Kubernetes (small) | Integration testing, pre-prod validation |
| **Production** | Kubernetes (HA) | Live traffic, auto-scaling, full observability |

---

## Docker Compose Architecture (Development)

```mermaid
flowchart TD
    subgraph DockerNetwork["Docker Bridge Network: multiagent-net"]
        NGINX["nginx:alpine\nReverse Proxy\nPort 80/443"]

        subgraph Frontend["Frontend"]
            NEXT["next-app:15\nPort 3000"]
        end

        subgraph Backend["Backend Services"]
            FASTAPI["fastapi-api\nPort 8000\n(4 workers)"]
            ORCH["orchestrator-service\nPort 8001"]
            AGENTS["agent-worker\n(replicas: 4)\nPort 8002-8005"]
        end

        subgraph Storage["Data Services"]
            PG["postgres:16\nPort 5432\nVolume: pgdata"]
            REDIS["redis:7-alpine\nPort 6379\nVolume: redisdata"]
            QDRANT["qdrant/qdrant:latest\nPort 6333\nVolume: qdrantdata"]
        end

        subgraph Observability["Observability Stack"]
            PROM["prom/prometheus\nPort 9090"]
            GRAF["grafana/grafana\nPort 3001"]
            LOKI["grafana/loki\nPort 3100"]
            JAEGER["jaegertracing/all-in-one\nPort 16686"]
        end
    end

    NGINX --> NEXT
    NGINX --> FASTAPI
    FASTAPI --> ORCH
    ORCH --> AGENTS
    AGENTS --> PG
    AGENTS --> REDIS
    AGENTS --> QDRANT
    FASTAPI --> REDIS
    PROM --> FASTAPI
    PROM --> AGENTS
    GRAF --> PROM
    GRAF --> LOKI
    JAEGER --> FASTAPI
```

---

## Kubernetes Production Architecture

```mermaid
flowchart TB
    subgraph Internet["Internet"]
        USERS[End Users]
    end

    subgraph CloudLB["Cloud Load Balancer"]
        LB["AWS ALB / GCP LB\n(TLS Termination)"]
    end

    subgraph K8sCluster["Kubernetes Cluster"]
        subgraph IngressNS["ingress-nginx Namespace"]
            INGRESS["Nginx Ingress Controller"]
        end

        subgraph AppNS["app Namespace"]
            subgraph FrontendDeploy["Frontend Deployment"]
                NEXT1["next-app Pod 1"]
                NEXT2["next-app Pod 2"]
            end

            subgraph APIDepoly["API Deployment (HPA: 2–10 pods)"]
                API1["fastapi-api Pod 1"]
                API2["fastapi-api Pod 2"]
                APIN["fastapi-api Pod N"]
            end

            subgraph OrchestratorDeploy["Orchestrator Deployment (HPA: 2–5)"]
                ORC1["orchestrator Pod 1"]
                ORC2["orchestrator Pod 2"]
            end

            subgraph AgentDeploy["Agent Worker Deployment (HPA: 4–20)"]
                AG1["agent-worker Pod 1"]
                AG2["agent-worker Pod 2"]
                AGN["agent-worker Pod N"]
            end
        end

        subgraph DataNS["data Namespace"]
            PG_SS["PostgreSQL StatefulSet\nPrimary + 2 Replicas"]
            REDIS_SS["Redis StatefulSet\nSentinel HA 3-node"]
            QDRANT_SS["Qdrant StatefulSet\n3-node cluster"]
        end

        subgraph ObsNS["observability Namespace"]
            PROMETHEUS["Prometheus\n+ AlertManager"]
            GRAFANA["Grafana"]
            OTEL_COL["OpenTelemetry Collector"]
        end

        subgraph SecurityNS["cert-manager + Vault"]
            CERTMGR["cert-manager\n(TLS automation)"]
            VAULT["HashiCorp Vault\n(secrets management)"]
        end
    end

    USERS --> LB
    LB --> INGRESS
    INGRESS --> NEXT1 & NEXT2
    INGRESS --> API1 & API2 & APIN
    API1 & API2 & APIN --> ORC1 & ORC2
    ORC1 & ORC2 --> AG1 & AG2 & AGN
    AG1 & AG2 & AGN --> PG_SS
    AG1 & AG2 & AGN --> REDIS_SS
    AG1 & AG2 & AGN --> QDRANT_SS
    CERTMGR --> INGRESS
    VAULT --> API1
```

---

## CI/CD Pipeline

```mermaid
flowchart LR
    subgraph Dev["Developer"]
        CODE[Git Push\nto feature branch]
    end

    subgraph CI["GitHub Actions CI"]
        PR[Pull Request\nOpened]
        LINT[Lint + Type Check\n(ruff, mypy, eslint)]
        TEST[Unit Tests\n(pytest, jest)]
        BUILD[Docker Build\n(multi-stage)]
        SCAN[Security Scan\n(Trivy, Semgrep)]
        INT[Integration Tests\n(docker-compose up)]
    end

    subgraph CD["Continuous Delivery"]
        MERGE[Merge to main]
        TAG[Semantic Version\nTag (v1.2.3)]
        PUSH[Push to\nContainer Registry\n(ECR / GCR)]
        STAGE[Deploy to\nStaging (auto)]
        E2E[E2E Tests\n(Playwright)]
        PROD[Deploy to\nProduction (manual gate)]
    end

    CODE --> PR
    PR --> LINT
    LINT --> TEST
    TEST --> BUILD
    BUILD --> SCAN
    SCAN --> INT
    INT -->|All pass| MERGE
    MERGE --> TAG
    TAG --> PUSH
    PUSH --> STAGE
    STAGE --> E2E
    E2E -->|Approved| PROD
```

---

## Horizontal Pod Autoscaler Configuration

| Service | Min Replicas | Max Replicas | Scale Metric | Target |
|---|---|---|---|---|
| `fastapi-api` | 2 | 10 | CPU Utilization | 70% |
| `orchestrator` | 2 | 5 | CPU + Memory | 75% |
| `agent-worker` | 4 | 20 | Redis queue depth | < 100 tasks/pod |
| `next-app` | 2 | 6 | CPU Utilization | 70% |

---

## Resource Requests & Limits

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---|---|---|---|---|
| `fastapi-api` | 500m | 2000m | 512Mi | 2Gi |
| `orchestrator` | 1000m | 4000m | 1Gi | 4Gi |
| `agent-worker` | 2000m | 8000m | 2Gi | 8Gi |
| `next-app` | 250m | 1000m | 256Mi | 1Gi |
| `postgres` | 2000m | 8000m | 4Gi | 16Gi |
| `redis` | 500m | 2000m | 512Mi | 4Gi |
| `qdrant` | 1000m | 4000m | 2Gi | 8Gi |

---

## Disaster Recovery Strategy

| Component | RTO | RPO | Strategy |
|---|---|---|---|
| PostgreSQL | < 1 hour | < 5 minutes | Streaming replication + hourly snapshots to S3 |
| Redis | < 15 minutes | < 1 minute | Redis Sentinel HA + AOF persistence |
| Qdrant | < 30 minutes | < 1 hour | Distributed snapshots to S3 |
| API Services | < 5 minutes | N/A (stateless) | Multi-AZ deployment, auto-restart |
| LangGraph State | < 10 minutes | < 30 seconds | PostgreSQL checkpointer |
