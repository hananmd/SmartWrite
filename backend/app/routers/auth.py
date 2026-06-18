"""Auth router: /api/register, /api/login, /api/logout, /api/me."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AUTH_COOKIE_NAME,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/api", tags=["auth"])
settings = get_settings()

_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _set_auth_cookie(response: Response, token: str) -> None:
    """Write the JWT into an httpOnly cookie on the response.

    secure=True only when DEBUG is False (i.e. production over HTTPS).
    Set DEBUG=true in .env for local HTTP development.
    """
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
        max_age=_COOKIE_MAX_AGE,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Create a new account, set an httpOnly auth cookie, and return the token."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Verify credentials, set an httpOnly auth cookie, and return the token."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Same error for bad email and bad password — avoids user enumeration.
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    token = create_access_token(user.id)
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    """Clear the auth cookie. The client should also discard any stored token."""
    response.delete_cookie(AUTH_COOKIE_NAME, samesite="lax")
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    """Return the current user's id and email. Used by the PWA to check auth state."""
    return {"id": current_user.id, "email": current_user.email}
