# Security Architecture — Master Overview

## Security Philosophy

The platform is built on **Zero Trust Architecture (ZTA)** principles:

> *"Never Trust, Always Verify — regardless of network location, service identity, or prior session."*

Every request traverses every security layer independently. Passing one layer grants no implicit trust in the next.

---

## Security Design Pillars

| Pillar | Implementation |
|---|---|
| **Identity** | JWT RS256 + API Keys with scoped permissions |
| **Access Control** | RBAC with resource-level permission checks |
| **Data Protection** | Encryption at rest (AES-256) + in transit (TLS 1.3) |
| **Threat Prevention** | WAF, input validation, prompt injection guard, rate limiting |
| **Observability** | Immutable audit logs, distributed tracing, anomaly alerts |
| **Secrets Hygiene** | Vault-injected secrets, no secrets in code or env files |
| **Resilience** | Defense-in-depth: 6 independent security layers |

---

## Defense-in-Depth Stack

```mermaid
flowchart TB
    INTERNET((Internet\nUntrusted)) --> L1

    subgraph L1["① Network Perimeter"]
        WAF["Web Application Firewall\nOWASP Core Rule Set v4\nGeo-blocking + IP reputation"]
        DDOS["DDoS Mitigation\nCloudflare / AWS Shield Advanced\nSYN flood · volumetric · slow-loris"]
        TLS["TLS 1.3 Termination\nHTTP Strict Transport Security\nHSTS max-age=31536000; includeSubDomains; preload"]
    end

    L1 --> L2

    subgraph L2["② API Gateway"]
        RATELIM["Rate Limiter\nRedis sliding window\nPer-user · per-IP · per-endpoint"]
        IPBLOCK["IP Allowlist / Blocklist\nDynamic blocklist updated on abuse detection"]
        HEADERVAL["Request Header Validation\nContent-Type · Content-Length · Host enforcement"]
    end

    L2 --> L3

    subgraph L3["③ Authentication"]
        JWT["JWT Verification\nRS256 signature · expiry · issuer · audience"]
        APIKEY["API Key Validation\nbcrypt hash lookup · scope check · expiry"]
        REFRESH["Refresh Token Guard\nRedis revocation check · jti blocklist"]
    end

    L3 --> L4

    subgraph L4["④ Authorization"]
        RBAC["RBAC Policy Engine\nRole · scope · resource ownership check"]
        ORGISO["Org Isolation\norg_id injected into every DB query"]
        RLS["PostgreSQL Row-Level Security\nDatabase-enforced multitenancy"]
    end

    L4 --> L5

    subgraph L5["⑤ Application"]
        INPUTVAL["Input Validation\nPydantic v2 schema enforcement\nSQL injection · XSS prevention"]
        PROMPTGUARD["Prompt Injection Guard\nPattern detection · semantic classifier"]
        OUTPUTFILTER["Output Sanitization\nContent filtering before API response"]
    end

    L5 --> L6

    subgraph L6["⑥ Data Layer"]
        ENCATREST["Encryption at Rest\nAES-256 via OS + cloud KMS\nPII field-level encryption"]
        MTLS["mTLS Between Services\nAll internal service calls mutual TLS\ncert-manager automated rotation"]
        PARAMQUERY["Parameterized Queries Only\nNo raw SQL string concatenation\nSQLAlchemy ORM enforced"]
    end

    subgraph OBS["Observability & Response"]
        AUDIT["Immutable Audit Logs\n(PostgreSQL partitioned)"]
        SIEM["SIEM Integration\nStructured logs → Loki → Grafana alerts"]
        INCIDENT["Incident Response\nPagerDuty · auto-isolate on critical"]
    end

    L6 --> AUDIT
    L1 & L2 & L3 & L4 & L5 --> SIEM
```

---

## Security Component Map

```mermaid
flowchart LR
    subgraph Client["Client Layer"]
        BROWSER["Browser\nSPA (Next.js)"]
        MOBILE["API Consumer\n(Postman / SDK)"]
    end

    subgraph Gateway["Security Gateway"]
        NGINX["Nginx + WAF\n(ModSecurity)"]
        FASTAPI["FastAPI\nSecurity Middleware Stack"]
    end

    subgraph AuthLayer["Authentication Layer"]
        AUTHSVC["Auth Service\nJWT issue · refresh · revoke"]
        JWTLIB["JWT Library\npython-jose (RS256)"]
        HASHLIB["Password Hashing\nbcrypt (rounds=12)"]
    end

    subgraph SecretStore["Secrets Store"]
        VAULT["HashiCorp Vault\nDynamic secrets\nAuto rotation"]
        KMS["Cloud KMS\nKey encryption keys"]
    end

    subgraph Storage["Data Layer"]
        REDIS["Redis\nRate limits · token blocklist\nSession cache"]
        POSTGRES["PostgreSQL\nRLS policies\nField encryption"]
        AUDIT_T["Audit Logs\n(append-only partition)"]
    end

    BROWSER & MOBILE --> NGINX
    NGINX --> FASTAPI
    FASTAPI --> AUTHSVC
    AUTHSVC --> JWTLIB
    AUTHSVC --> HASHLIB
    AUTHSVC --> REDIS
    FASTAPI --> REDIS
    FASTAPI --> POSTGRES
    FASTAPI --> AUDIT_T
    AUTHSVC & FASTAPI --> VAULT
    VAULT --> KMS
```

---

## Security Non-Negotiables

> [!IMPORTANT]
> The following are absolute requirements — violations trigger immediate security review.

| Rule | Enforcement |
|---|---|
| TLS 1.2+ required on all connections | Nginx `ssl_protocols TLSv1.2 TLSv1.3;` |
| Passwords never stored in plaintext | bcrypt with minimum 12 rounds |
| Secrets never in code or `.env` files | Vault dynamic injection at startup |
| All DB queries parameterized | SQLAlchemy ORM — no `text()` with user input |
| JWT signed with RS256 (not HS256) | RS256 allows public key verification without sharing secret |
| Refresh tokens are single-use | Redis jti tracking — old token immediately invalidated on use |
| All mutations produce audit records | AuditService called in every service mutating method |
| Org isolation on every DB query | `org_id` filter injected by DI, enforced by RLS |
| No sensitive data in logs | PII fields masked before structured log emission |
| No secrets in HTTP headers or URLs | API keys in `Authorization` header only, never query params |
