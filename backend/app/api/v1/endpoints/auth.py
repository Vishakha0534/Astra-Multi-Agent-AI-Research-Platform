from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.user import LoginRequest, RefreshTokenRequest, TokenResponse, UserCreate, UserProfile
from app.services.user_service import UserService
from app.core.security import decode_token, create_access_token
from app.core.exceptions import InvalidTokenError
from app.core.config import settings

router = APIRouter()


@router.post("/register", response_model=UserProfile, status_code=201, summary="Register a new user")
async def register(data: UserCreate, db: DBSession) -> UserProfile:
    service = UserService(db)
    user = await service.create_user(data)
    return UserProfile.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="Authenticate and get JWT tokens")
async def login(data: LoginRequest, db: DBSession) -> TokenResponse:
    service = UserService(db)
    return await service.authenticate(data)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(data: RefreshTokenRequest, db: DBSession) -> TokenResponse:
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise InvalidTokenError("Expected refresh token")

    import uuid
    from app.repositories.user_repository import UserRepository
    from app.core.security import create_refresh_token

    user_id = uuid.UUID(payload["sub"])
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user or not user.is_active:
        raise InvalidTokenError("User not found or inactive")

    extra_claims = {"role": user.role, "org_id": str(user.org_id)}
    access_token = create_access_token(str(user.id), extra=extra_claims)
    refresh = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserProfile, summary="Get current user profile")
async def get_me(current_user: CurrentUser) -> UserProfile:
    return UserProfile.model_validate(current_user)
