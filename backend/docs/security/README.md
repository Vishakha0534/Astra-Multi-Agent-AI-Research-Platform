# Security Architecture — Index
## Phase - 2 (Security and authentication)

> **Security Architect Design Document**
> Methodology: STRIDE · Zero Trust · OWASP Top 10 · Defense-in-Depth
> Version: 1.0.0 | Classification: Internal — Restricted

---

## Document Index

| # | Document | Description |
|---|---|---|
| 01 | [Security Architecture](./01_security_architecture.md) | Defense-in-depth stack, 6-layer security model, component map, non-negotiables |
| 02 | [Authentication Flow](./02_authentication_flow.md) | JWT RS256 design, registration, login, refresh rotation, logout, API key auth, session policy |
| 03 | [Authorization Design](./03_authorization_design.md) | RBAC matrix, project roles, API key scopes, org isolation, privilege escalation prevention |
| 04 | [Middleware Design](./04_middleware_design.md) | 7-layer middleware stack, CORS, HTTPS, rate limiting, input validation, prompt injection guard |
| 05 | [Threat Model](./05_threat_model.md) | STRIDE analysis across 6 attack categories, 34 individual threats, incident response triggers |
| 06 | [Security Best Practices](./06_security_best_practices.md) | Secrets management (Vault), password policy, TLS config, audit log integrity, OWASP coverage |

---

## Security at a Glance

### Authentication
| Method | Token Lifetime | Algorithm | Revocable |
|---|---|---|---|
| JWT Access Token | 15 minutes | RS256 | Via Redis jti blocklist |
| JWT Refresh Token | 7 days | HS256 | Single-use rotation; Redis |
| API Key | Until revoked/expired | SHA-256 hash lookup | Immediate |

### Authorization Roles
| Role | Scope |
|---|---|
| `superadmin` | Full platform — all orgs |
| `admin` | Full org — all resources within org |
| `researcher` | Own projects and jobs; create/manage |
| `viewer` | Read-only to org/project resources |

### Rate Limits
| Tier | Limit | Window |
|---|---|---|
| Auth endpoints | 10 req | 1 min |
| Per user (normal) | 60 req | 1 min |
| Per user (burst) | 1,000 req | 1 hour |
| API key | 200 req | 1 min |
| IP (unauthenticated) | 30 req | 1 min |

### STRIDE Coverage
| Category | Threats Identified | Mitigated |
|---|---|---|
| Spoofing | 8 | 8 |
| Tampering | 9 | 9 |
| Repudiation | 2 | 2 |
| Information Disclosure | 6 | 6 |
| Denial of Service | 7 | 7 |
| Elevation of Privilege | 6 | 6 |
| **Total** | **38** | **38** |

---

## Key Security Decisions

| Decision | Rationale |
|---|---|
| **RS256 over HS256** | Public key can verify tokens without sharing secret — safe for multi-service distribution |
| **Refresh token rotation** | Stolen token detection: re-use of a revoked token triggers full session termination |
| **Dual org isolation** | App-layer `org_id` filter + DB-layer RLS — one bug in either layer doesn't break isolation |
| **Separate audit session** | Audit records commit independently — persist even when business transaction rolls back |
| **Vault dynamic secrets** | DB credentials auto-rotate every hour — leaked cred has minimal exposure window |
| **bcrypt pepper** | Leaked password hash DB still can't be cracked without the pepper secret |
| **Prompt injection guard** | AI platforms uniquely vulnerable — pattern + semantic classifier as dual gate |
| **Immutable audit log** | PostgreSQL append-only via RLS + WORM S3 archive — tamper-evident 7-year trail |
