# Security Architecture — Authentication Flow

## Authentication Methods

The platform supports two authentication methods, each with distinct use cases:

| Method | Use Case | Token Lifetime | Revocable |
|---|---|---|---|
| **JWT (Bearer)** | Human users via browser/app | Access: 15 min · Refresh: 7 days | ✅ Via Redis blocklist |
| **API Key** | CI/CD, integrations, agent workers | Until expiry date or revocation | ✅ Immediate |

---

## JWT Architecture

### Token Design

**Access Token** — RS256 signed, short-lived (15 min), stateless verification:

```
Header:  { "alg": "RS256", "typ": "JWT", "kid": "key-2026-06" }
Payload: {
  "sub":    "550e8400-e29b-41d4-a716-446655440000",  // user UUID
  "email":  "alice@acme.com",
  "role":   "researcher",
  "org_id": "org-uuid",
  "scopes": ["read:projects", "write:jobs"],
  "jti":    "unique-jwt-id",                          // JWT ID for revocation
  "iss":    "https://api.platform.com",
  "aud":    "https://api.platform.com",
  "iat":    1717416000,
  "exp":    1717416900                                 // iat + 900s (15 min)
}
```

**Refresh Token** — HS256 signed, long-lived (7 days), server-side tracked:
- Stored as `sha256(token)` hash in Redis with TTL
- Every use issues a new pair and **revokes the old refresh token** (rotation)
- Stolen refresh token detection: re-use of revoked token → revoke entire family

---

## RS256 Key Management

```mermaid
flowchart LR
    subgraph KeyGen["Key Generation (one-time)"]
        GEN["openssl genrsa 4096\n→ private_key.pem"]
        PUB["openssl rsa -pubout\n→ public_key.pem"]
        GEN --> PUB
    end

    subgraph Vault["HashiCorp Vault"]
        PRIV["vault kv put secret/jwt\nprivate_key=@private_key.pem"]
        PUBK["vault kv put secret/jwt\npublic_key=@public_key.pem"]
    end

    subgraph Runtime["Service Runtime"]
        API["FastAPI Service\nreads private key at startup\nsigns access tokens"]
        VERIFIER["Any service\nreads public key\nverifies tokens — no secret shared"]
    end

    GEN --> PRIV
    PUB --> PUBK
    PRIV -->|Dynamic secret injection| API
    PUBK -->|Public key distribution| VERIFIER
```

**Key Rotation Schedule**: Every 90 days. Vault manages versioned keys. `kid` (Key ID) in JWT header allows multi-key validation during rotation window.

---

## Registration & Email Verification Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Frontend
    participant API as FastAPI
    participant AUTH as AuthService
    participant DB as PostgreSQL
    participant REDIS as Redis
    participant EMAIL as Email Service

    User->>FE: Fill registration form
    FE->>API: POST /auth/register\n{org_name, email, username, password}

    API->>API: Pydantic validation\n(email format, password strength)
    API->>DB: SELECT user WHERE email=? AND org_id=?
    DB-->>API: No duplicate found

    API->>AUTH: hash_password(password)\nbcrypt rounds=12
    AUTH-->>API: password_hash

    API->>DB: INSERT organization\nINSERT user (status=pending_verification)
    DB-->>API: user record created

    API->>REDIS: SETEX auth:verify:{token} 86400 {user_id}
    API->>EMAIL: send_verification_email(email, token)

    API-->>FE: 201 Created\n{user_id, "Verification email sent"}

    Note over User,EMAIL: User receives email, clicks link

    User->>FE: Click verify link
    FE->>API: GET /auth/verify-email?token={token}
    API->>REDIS: GET auth:verify:{token}
    REDIS-->>API: user_id (found, TTL valid)
    API->>DB: UPDATE user\nstatus=active\nemail_verified_at=NOW()
    API->>REDIS: DEL auth:verify:{token}
    API-->>FE: 200 OK "Email verified"
```

---

## Login & Token Issuance Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI
    participant AUTH as AuthService
    participant DB as PostgreSQL
    participant REDIS as Redis

    User->>API: POST /auth/login\n{email, password}

    API->>DB: SELECT user WHERE email=?\nAND org_id=?\nAND deleted_at IS NULL
    DB-->>API: User record

    API->>API: Check status = 'active'
    API->>API: Check locked_until < NOW()

    alt Account locked
        API-->>User: 403 Forbidden\n"Account temporarily locked"
    end

    API->>AUTH: bcrypt.verify(password, hash)

    alt Password invalid
        API->>DB: UPDATE user\nfailed_login_count += 1\n[if count>=5: set locked_until]
        API->>DB: INSERT audit_log (action=login, result=failure)
        API-->>User: 401 Unauthorized\n"Invalid credentials"
    end

    API->>DB: UPDATE user\nfailed_login_count=0\nlast_login_at=NOW()

    API->>AUTH: generate_access_token(claims, private_key)
    Note right of AUTH: RS256 signed\nexp = now + 15min

    API->>AUTH: generate_refresh_token(user_id, jti)
    Note right of AUTH: HS256 signed\nexp = now + 7days

    API->>REDIS: SETEX auth:refresh:{user_id}:{jti}\n604800 "valid"

    API->>DB: INSERT audit_log (action=login, result=success)

    API-->>User: 200 OK\n{access_token, refresh_token,\ntoken_type, expires_in}
```

---

## Token Refresh (Rotation) Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI
    participant AUTH as AuthService
    participant REDIS as Redis
    participant DB as PostgreSQL

    Client->>API: POST /auth/refresh\n{refresh_token}

    API->>AUTH: decode_refresh_token(token)
    Note right of AUTH: Verifies HS256 signature\nExtracts user_id, jti, exp

    alt Token expired or invalid signature
        API-->>Client: 401 Unauthorized\nTOKEN_EXPIRED
    end

    API->>REDIS: GET auth:refresh:{user_id}:{jti}

    alt Token not found in Redis (revoked)
        Note over API,REDIS: ⚠️ Possible token theft detected
        API->>REDIS: DEL auth:refresh:{user_id}:*\n(revoke all refresh tokens for user)
        API->>DB: INSERT audit_log\n(action=login, result=failure\nfailure_reason="refresh_token_reuse")
        API-->>Client: 401 Unauthorized\n"Session invalidated — please login again"
    end

    API->>REDIS: DEL auth:refresh:{user_id}:{jti}
    Note right of API: Immediately invalidate old token

    API->>DB: SELECT user WHERE id=?\nAND status='active'
    DB-->>API: User record (fresh claims)

    API->>AUTH: generate_access_token(fresh_claims)
    API->>AUTH: generate_refresh_token(user_id, new_jti)
    API->>REDIS: SETEX auth:refresh:{user_id}:{new_jti} 604800 "valid"

    API-->>Client: 200 OK\n{new_access_token, new_refresh_token}
```

---

## Logout & Token Revocation Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI
    participant REDIS as Redis
    participant DB as PostgreSQL

    Client->>API: POST /auth/logout\nAuthorization: Bearer {access_token}\n{refresh_token}

    API->>API: Verify access token\nExtract jti, user_id, exp

    API->>REDIS: SETEX auth:blocklist:{access_jti}\n{remaining_ttl} "revoked"
    Note right of REDIS: Access token blocked until its own expiry

    API->>API: Decode refresh_token\nExtract refresh_jti

    API->>REDIS: DEL auth:refresh:{user_id}:{refresh_jti}
    Note right of REDIS: Refresh token immediately invalidated

    API->>DB: INSERT audit_log (action=logout)

    API-->>Client: 204 No Content
```

---

## API Key Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    actor CI as CI/CD System
    participant API as FastAPI
    participant DB as PostgreSQL
    participant REDIS as Redis

    Note over CI: API Key format:\n"ma_live_sk_{random_32_chars}"

    CI->>API: GET /projects\nAuthorization: Bearer ma_live_sk_abc123...

    API->>API: Detect API key prefix\n(not a JWT — no "." separators)

    API->>API: sha256(raw_key) → key_hash

    API->>REDIS: GET apikey:{key_hash}
    Note right of REDIS: Cache hit avoids DB round-trip\nTTL = 5 minutes

    alt Cache miss
        API->>DB: SELECT api_keys WHERE key_hash=?\nAND is_active=TRUE\nAND (expires_at IS NULL OR expires_at > NOW())
        DB-->>API: APIKey record (with user_id, scopes)
        API->>REDIS: SETEX apikey:{key_hash} 300 {serialized_record}
    end

    API->>API: Check requested endpoint scope\nvs key.scopes

    alt Scope insufficient
        API-->>CI: 403 Forbidden\n"Insufficient API key scope"
    end

    API->>DB: UPDATE api_keys\nSET last_used_at=NOW()\nWHERE id=?

    API->>API: Construct JWTClaims-equivalent\nfrom APIKey user record

    API-->>CI: 200 OK + Response data
```

---

## Password Security Policy

| Policy | Requirement |
|---|---|
| **Minimum length** | 10 characters |
| **Maximum length** | 128 characters (prevent DoS via bcrypt long-input attack) |
| **Complexity** | At least 1 uppercase, 1 lowercase, 1 digit, 1 special character |
| **Algorithm** | bcrypt with work factor 12 (re-evaluated annually) |
| **History** | Last 5 passwords cannot be reused |
| **Reset tokens** | Cryptographically random 32-byte tokens, TTL = 1 hour, single-use |
| **Brute force** | Lock account after 5 failures for 30 minutes |
| **Leak detection** | Check against Have I Been Pwned API (k-anonymity model) on registration |

---

## Session Security Checklist

| Control | Implementation |
|---|---|
| Access token short-lived | 15 minutes maximum |
| Refresh token rotation | Single-use; old token revoked on every refresh |
| Concurrent session limit | Max 5 active refresh tokens per user (Redis key count) |
| Geographic anomaly | Flag login from new country → require re-verification |
| Idle timeout | Refresh token revoked after 7 days of non-use |
| Forced logout | Admin can `DEL auth:refresh:{user_id}:*` to terminate all sessions |
| Token binding | `iss` and `aud` claims validated to prevent token relay attacks |
