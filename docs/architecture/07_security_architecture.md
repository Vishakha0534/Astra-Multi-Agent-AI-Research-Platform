# 7. Security Architecture

## Security Design Philosophy

The platform follows a **Zero Trust Architecture (ZTA)** model: every request is authenticated, every action is authorized, and no implicit trust is granted based on network location or service identity.

---

## Defense-in-Depth Layers

```mermaid
flowchart TB
    INTERNET((Internet)) --> L1

    subgraph L1["Layer 1: Network Perimeter"]
        WAF["Web Application Firewall\n(OWASP Rule Set)"]
        DDOS["DDoS Protection\n(Cloudflare / AWS Shield)"]
        TLS["TLS 1.3 Termination"]
    end

    L1 --> L2

    subgraph L2["Layer 2: API Gateway"]
        RATELIM["Rate Limiting\n(Redis sliding window)"]
        IPBLOCK["IP Blocklist / Allowlist"]
        REQUESTVAL["Request Validation\n(Pydantic schemas)"]
    end

    L2 --> L3

    subgraph L3["Layer 3: Authentication & Authorization"]
        JWT["JWT Verification\n(RS256 signed)"]
        RBAC["RBAC Policy Engine\n(role + scope checks)"]
        APIKEY["API Key Validation\n(hashed lookup)"]
    end

    L3 --> L4

    subgraph L4["Layer 4: Application Logic"]
        INPUTSAN["Input Sanitization\n(XSS, injection prevention)"]
        PROMPTINJ["Prompt Injection Guard\n(LLM input filtering)"]
        OUTPUTVAL["Output Validation\n(schema + content filter)"]
    end

    L4 --> L5

    subgraph L5["Layer 5: Data Layer"]
        ENCATREST["Encryption at Rest\n(AES-256)"]
        ENCINTRANSIT["Encryption in Transit\n(mTLS between services)"]
        ROWSEC["Row-Level Security\n(PostgreSQL RLS)"]
        FIELDENC["Field Encryption\n(PII fields)"]
    end
```

---

## Authentication & Authorization

### JWT Token Structure

```mermaid
classDiagram
    class JWTClaims {
        +str sub (user_id)
        +str email
        +UserRole role
        +str org_id
        +list~str~ scopes
        +int iat (issued_at)
        +int exp (expires)
        +str jti (jwt_id)
        +str iss (issuer)
        +str aud (audience)
    }

    class TokenPair {
        +str access_token (15 min, RS256)
        +str refresh_token (7 days, HS256)
        +str token_type = "Bearer"
        +int expires_in
    }
```

### RBAC Permission Matrix

| Resource | Researcher | Org Admin | Platform Admin |
|---|---|---|---|
| Create research session | ✅ Own | ✅ Org | ✅ All |
| View research session | ✅ Own | ✅ Org | ✅ All |
| Delete research session | ✅ Own | ✅ Org | ✅ All |
| Upload knowledge documents | ✅ Own | ✅ Org | ✅ All |
| Manage org members | ❌ | ✅ Org | ✅ All |
| Manage model registry | ❌ | ❌ | ✅ All |
| View usage/billing | ❌ | ✅ Org | ✅ All |
| Access audit logs | ❌ | ✅ Org | ✅ All |
| Manage platform config | ❌ | ❌ | ✅ All |

---

## Prompt Injection Defense

```mermaid
flowchart LR
    INPUT[User Research Query] --> GUARD[Prompt Injection Guard]

    GUARD --> CHECK1{Contains\nInstruction Override?}
    CHECK1 -->|Yes| BLOCK1[BLOCK + Log Alert]
    CHECK1 -->|No| CHECK2{Contains\nSystem Prompt Leak?}
    CHECK2 -->|Yes| BLOCK2[BLOCK + Log Alert]
    CHECK2 -->|No| CHECK3{Contains\nRole-Play Escape?}
    CHECK3 -->|Yes| SANITIZE[Sanitize + Warn]
    CHECK3 -->|No| CHECK4{Token Count\nExceeds Budget?}
    CHECK4 -->|Yes| TRUNCATE[Truncate to Budget]
    CHECK4 -->|No| PASS[Pass to Orchestrator]

    SANITIZE --> PASS
    TRUNCATE --> PASS
```

### Injection Pattern Detection Rules

| Pattern Category | Detection Method | Action |
|---|---|---|
| Direct override (`ignore previous`) | Regex + semantic similarity | Block |
| Jailbreak (`DAN`, role-play escapes) | Classifier model | Block |
| System prompt extraction | Pattern matching | Block |
| Indirect injection via documents | Content scanning at upload | Block |
| Token stuffing | Token count threshold | Truncate |
| Encoding attacks (Base64, Unicode) | Normalize + re-check | Sanitize |

---

## Service-to-Service Security (mTLS)

```mermaid
flowchart TD
    subgraph ServiceMesh["Service Mesh (Istio / Linkerd)"]
        API["FastAPI Service\n(cert: api-service.local)"]
        ORC["Orchestrator Service\n(cert: orchestrator.local)"]
        AGENTS["Agent Service\n(cert: agents.local)"]
        PG["PostgreSQL\n(cert: postgres.local)"]
        REDIS["Redis\n(cert: redis.local)"]
        QDRANT["Qdrant\n(cert: qdrant.local)"]
    end

    API <-->|mTLS| ORC
    ORC <-->|mTLS| AGENTS
    AGENTS <-->|mTLS| PG
    AGENTS <-->|mTLS| REDIS
    AGENTS <-->|mTLS| QDRANT

    CA["Internal Certificate Authority\n(cert-manager)"] -->|issues certs| API
    CA -->|issues certs| ORC
    CA -->|issues certs| AGENTS
    CA -->|issues certs| PG
    CA -->|issues certs| REDIS
    CA -->|issues certs| QDRANT
```

---

## Secrets Management

```mermaid
flowchart LR
    subgraph SecretsVault["HashiCorp Vault / AWS Secrets Manager"]
        S1["LLM API Keys\n(per provider)"]
        S2["Database Credentials\n(rotated every 30d)"]
        S3["JWT Signing Keys\n(RS256 key pair)"]
        S4["Service Account Tokens"]
        S5["Encryption Keys (KMS)"]
    end

    subgraph Services["Platform Services"]
        API[FastAPI]
        ORC[Orchestrator]
        AGENTS[Agent Fleet]
    end

    SecretsVault -->|Dynamic secret injection\nat startup| API
    SecretsVault -->|Dynamic secret injection\nat startup| ORC
    SecretsVault -->|Dynamic secret injection\nat startup| AGENTS

    note["Secrets NEVER stored in:\n- Environment files (.env)\n- Docker images\n- Git repositories\n- Application logs"]
```

---

## Data Privacy & Compliance

| Requirement | Implementation |
|---|---|
| **PII Protection** | User email, name encrypted with application-level AES-256 |
| **GDPR Right to Erasure** | Soft delete + async PII scrubber job |
| **Data Residency** | Org-level configuration for data region (EU, US, APAC) |
| **LLM Data Policy** | No training data submission; API calls use `no-log` flags where available |
| **Audit Trail** | All mutations logged to immutable `audit_logs` table |
| **Encryption at Rest** | PostgreSQL + Qdrant volumes encrypted (AES-256 via OS/cloud) |
| **Key Rotation** | Automated 90-day rotation via Vault + cert-manager |
| **SOC 2 Type II** | Audit log completeness, access control reviews, incident response |

---

## Security Incident Response Flow

```mermaid
flowchart TD
    ALERT[Security Alert Triggered] --> TRIAGE{Severity Level}

    TRIAGE -->|Critical| IMMEDIATE[Immediate Response\n< 15 minutes]
    TRIAGE -->|High| URGENT[Urgent Response\n< 1 hour]
    TRIAGE -->|Medium| STANDARD[Standard Response\n< 24 hours]
    TRIAGE -->|Low| SCHEDULED[Scheduled Review]

    IMMEDIATE --> ISOLATE[Isolate affected service]
    ISOLATE --> REVOKE[Revoke compromised credentials]
    REVOKE --> FORENSICS[Collect forensic snapshots]
    FORENSICS --> RESTORE[Restore from last known-good state]
    RESTORE --> POSTMORTEM[Write blameless post-mortem]
```
