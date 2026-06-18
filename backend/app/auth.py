"""Auth utilities: password hashing, JWT creation/verification, request dependency.

Password hashing uses stdlib hashlib.pbkdf2_hmac (SHA-256) so there is no
dependency on passlib, which has known issues with Python 3.13+.

JWT uses PyJWT with HS256. Only short-lived access tokens are minted here;
a refresh-token flow is deferred to a later milestone (see CLAUDE.md).
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.database import get_db

settings = get_settings()

# auto_error=False so the PWA's cookie path doesn't get a 403 on missing header.
_bearer = HTTPBearer(auto_error=False)

ACCESS_TOKEN_EXPIRE_MINUTES = 30
AUTH_COOKIE_NAME = "smartwrite_token"
_ALGORITHM = "HS256"
_ITERATIONS = 600_000


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return a storable hash string: pbkdf2_sha256$<iters>$<salt>$<hex-dk>."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    """Constant-time check of a plaintext password against a stored hash."""
    try:
        _, iters_str, salt, stored_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), int(iters_str))
        return hmac.compare_digest(dk.hex(), stored_hex)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(user_id: int) -> str:
    """Mint a signed HS256 JWT that expires in ACCESS_TOKEN_EXPIRE_MINUTES."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """Validate the Bearer token or httpOnly cookie and return the authenticated User row.

    Checks Authorization: Bearer first (Chrome extension path), then falls
    back to the smartwrite_token httpOnly cookie (PWA path).
    """
    from backend.app.models.user import User  # local import avoids circular dep

    token = credentials.credentials if credentials else None
    if not token:
        token = request.cookies.get(AUTH_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
