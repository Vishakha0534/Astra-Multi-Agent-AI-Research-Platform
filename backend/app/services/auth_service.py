from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError as AstraValidationError,
)
from app.core.security import get_password_hash, verify_password
from app.database.redis import RedisCache
from app.models.auth import AuditLog, UserSession
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.session_manager import SessionManager
from app.services.token_manager import TokenManager

logger = structlog.get_logger(__name__)

# ─── Brute-force protection (Redis keys) ─────────────────────────────────────
_BF_PREFIX_EMAIL = "bf:email:"
_BF_PREFIX_IP = "bf:ip:"
_BF_MAX_EMAIL_FAILURES = 5
_BF_MAX_IP_FAILURES = 20
_BF_WINDOW_SECONDS = 900    # 15 min sliding window
_BF_LOCKOUT_SECONDS = 1800  # 30 min lockout


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class AuthService:
    """Complete authentication service."""

    def __init__(
        self,
        db: AsyncSession,
        cache: RedisCache,
    ) -> None:
        self.db = db
        self.cache = cache
        self.token_manager = TokenManager(cache)
        self.session_manager = SessionManager(db, cache)

    # ─── Brute-force Helpers ──────────────────────────────────────────────────

    async def _check_brute_force(self, email: str, ip: str) -> None:
        """Raise AuthenticationError if email or IP is locked out."""
        email_key = f"{_BF_PREFIX_EMAIL}{_sha256(email)}"
        ip_key = f"{_BF_PREFIX_IP}{ip}"

        email_fails = int(await self.cache.get(email_key) or 0)
        ip_fails = int(await self.cache.get(ip_key) or 0)

        if email_fails >= _BF_MAX_EMAIL_FAILURES:
            raise AuthenticationError(
                "Account temporarily locked due to too many failed attempts. "
                "Please try again in 30 minutes."
            )
        if ip_fails >= _BF_MAX_IP_FAILURES:
            raise AuthenticationError(
                "Too many failed attempts from your IP. Please try again later."
            )

    async def _record_failure(self, email: str, ip: str) -> None:
        redis = self.cache._client  # access raw client for INCR
        email_key = f"{_BF_PREFIX_EMAIL}{_sha256(email)}"
        ip_key = f"{_BF_PREFIX_IP}{ip}"
        await redis.incr(email_key)
        await redis.expire(email_key, _BF_LOCKOUT_SECONDS)
        await redis.incr(ip_key)
        await redis.expire(ip_key, _BF_LOCKOUT_SECONDS)

    async def _clear_failures(self, email: str) -> None:
        await self.cache.delete(f"{_BF_PREFIX_EMAIL}{_sha256(email)}")

    # ─── Audit Logging ────────────────────────────────────────────────────────

    async def _audit(
        self,
        event_type: str,
        outcome: str,
        *,
        user_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        extra: dict | None = None,
    ) -> None:
        log = AuditLog(
            event_type=event_type,
            event_outcome=outcome,
            user_id=user_id,
            org_id=org_id,
            ip_address=ip,
            user_agent=user_agent,
            extra_data=extra,
        )
        self.db.add(log)
        await self.db.flush()

    # ─── Registration ─────────────────────────────────────────────────────────

    async def register(
        self,
        payload: RegisterRequest,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Register a new user.

        Raises:
            ConflictError: If email or username already exists.
        """
        # Check uniqueness
        exists = await self.db.execute(
            select(User).where(User.email == payload.email.lower())
        )
        if exists.scalar_one_or_none():
            raise ConflictError("EMAIL_ALREADY_EXISTS", "A user with this email already exists")

        exists_uname = await self.db.execute(
            select(User).where(User.username == payload.username.lower())
        )
        if exists_uname.scalar_one_or_none():
            raise ConflictError("USERNAME_TAKEN", "This username is already taken")

        # Assign to default org if not provided (single-tenant bootstrap)
        org_id = payload.org_id or uuid.UUID(str(settings.DEFAULT_ORG_ID))

        user = User(
            email=payload.email.lower(),
            username=payload.username.lower(),
            hashed_password=get_password_hash(payload.password),
            full_name=payload.full_name,
            org_id=org_id,
            role=payload.role or "researcher",
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        # Create email verification token
        verify_token = await self.token_manager.create_email_verification_token(user.id)

        await self._audit(
            "user.register",
            "success",
            user_id=user.id,
            org_id=org_id,
            ip=ip,
            user_agent=user_agent,
            extra={"email": user.email},
        )

        logger.info("user_registered", user_id=str(user.id), email=user.email)

        # In production: send verify_token via email service
        # For now, log it (CI/CD pipelines pick up from log in dev)
        logger.info("email_verify_token_generated", token=verify_token, user_id=str(user.id))

        return user

    # ─── Email Verification ───────────────────────────────────────────────────

    async def verify_email(self, token: str) -> User:
        """Consume an email verification token and activate the user."""
        user_id = await self.token_manager.consume_email_verification_token(token)

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")

        user.is_verified = True
        self.db.add(user)
        await self.db.flush()

        await self._audit("user.email_verified", "success", user_id=user.id, org_id=user.org_id)
        return user

    # ─── Login ────────────────────────────────────────────────────────────────

    async def login(
        self,
        payload: LoginRequest,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        """Authenticate a user and issue access + refresh tokens."""
        await self._check_brute_force(payload.email, ip or "unknown")

        result = await self.db.execute(
            select(User).where(User.email == payload.email.lower())
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.hashed_password):
            await self._record_failure(payload.email, ip or "unknown")
            await self._audit(
                "user.login",
                "failure",
                ip=ip,
                user_agent=user_agent,
                extra={"email": payload.email},
            )
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is disabled. Contact your administrator.")

        await self._clear_failures(payload.email)

        # Mint tokens
        jti = str(uuid.uuid4())
        access_token, _ = self.token_manager.create_access_token(
            user_id=user.id, role=user.role, org_id=user.org_id, jti=jti
        )

        # Create DB session
        session = await self.session_manager.create_session(
            user_id=user.id,
            org_id=user.org_id,
            jti=jti,
            refresh_token_hash=_sha256(jti),  # temporary; updated below
            ip_address=ip,
            user_agent=user_agent,
        )

        refresh_token = await self.token_manager.create_refresh_token(
            user_id=user.id,
            jti=jti,
            session_id=str(session.id),
        )

        await self._audit(
            "user.login",
            "success",
            user_id=user.id,
            org_id=user.org_id,
            ip=ip,
            user_agent=user_agent,
        )
        logger.info("user_logged_in", user_id=str(user.id), role=user.role)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ─── Refresh ──────────────────────────────────────────────────────────────

    async def refresh_tokens(
        self,
        refresh_token: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        """Rotate refresh token and issue a new access token."""
        payload = await self.token_manager.validate_refresh_token(refresh_token)
        user_id = uuid.UUID(payload["user_id"])
        old_jti = payload["jti"]
        session_id = payload["session_id"]

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Blocklist old JTI
        remaining_ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        await self.token_manager.blocklist_jti(old_jti, ttl_seconds=remaining_ttl)

        # New tokens
        new_jti = str(uuid.uuid4())
        access_token, _ = self.token_manager.create_access_token(
            user_id=user.id, role=user.role, org_id=user.org_id, jti=new_jti
        )
        new_refresh = await self.token_manager.rotate_refresh_token(
            old_token=refresh_token,
            user_id=user.id,
            jti=new_jti,
            session_id=session_id,
        )

        # Update session JTI
        await self.session_manager.revoke_session(old_jti)
        await self.session_manager.create_session(
            user_id=user.id,
            org_id=user.org_id,
            jti=new_jti,
            refresh_token_hash=_sha256(new_jti),
            ip_address=ip,
            user_agent=user_agent,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type="Bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ─── Logout ───────────────────────────────────────────────────────────────

    async def logout(
        self,
        jti: str,
        refresh_token: str,
        user_id: uuid.UUID,
        *,
        all_devices: bool = False,
        ip: str | None = None,
    ) -> None:
        """Revoke the current session (or all sessions)."""
        # Blocklist current access token JTI
        await self.token_manager.blocklist_jti(
            jti, ttl_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        # Revoke refresh token
        await self.token_manager.revoke_refresh_token(refresh_token)
        # Revoke DB session
        await self.session_manager.revoke_session(jti)

        if all_devices:
            revoked = await self.session_manager.revoke_all_user_sessions(user_id)
            logger.info("logout_all_devices", user_id=str(user_id), sessions_revoked=revoked)

        await self._audit(
            "user.logout",
            "success",
            user_id=user_id,
            ip=ip,
            extra={"all_devices": all_devices},
        )

    # ─── Password Change ──────────────────────────────────────────────────────

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
        *,
        ip: str | None = None,
    ) -> None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        user.hashed_password = get_password_hash(new_password)
        self.db.add(user)
        await self.db.flush()

        # Force logout from all other sessions
        await self.session_manager.revoke_all_user_sessions(user_id)
        await self._audit("user.password_changed", "success", user_id=user_id, ip=ip)

    # ─── Password Reset ───────────────────────────────────────────────────────

    async def request_password_reset(self, email: str) -> str | None:
        """Generate a reset token. Returns None if email not found (no enumeration)."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()
        if not user:
            return None  # Silent — do not reveal account existence
        token = await self.token_manager.create_password_reset_token(user.id)
        logger.info("password_reset_token_generated", user_id=str(user.id))
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        user_id = await self.token_manager.consume_password_reset_token(token)
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User not found")
        user.hashed_password = get_password_hash(new_password)
        self.db.add(user)
        await self.db.flush()
        await self.session_manager.revoke_all_user_sessions(user_id)
        await self._audit("user.password_reset", "success", user_id=user_id)
