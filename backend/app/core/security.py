from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError

# ─── Password Hashing ────────────────────────────────────────────────────────

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)


def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of plain_password."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches hashed_password."""
    return _pwd_context.verify(plain_password, hashed_password)


# ─── JWT Tokens ──────────────────────────────────────────────────────────────

TokenPayload = dict[str, Any]


def create_access_token(
    subject: str,
    extra: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived JWT access token.

    Args:
        subject: User UUID (as string) used as the `sub` claim.
        extra:   Additional claims to embed (e.g., role, org_id).

    Returns:
        Signed JWT string.
    """
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: TokenPayload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
        **(extra or {}),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a long-lived JWT refresh token.

    Args:
        subject: User UUID (as string).

    Returns:
        Signed JWT string.
    """
    expire = datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload: TokenPayload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token.

    Args:
        token: Raw JWT string from Authorization header.

    Returns:
        Decoded token payload dict.

    Raises:
        TokenExpiredError: If token has expired.
        InvalidTokenError: If token is malformed or signature invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        if "expired" in str(exc).lower():
            raise TokenExpiredError() from exc
        raise InvalidTokenError() from exc
