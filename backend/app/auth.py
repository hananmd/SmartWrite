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
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.database import get_db

settings = get_settings()

_bearer = HTTPBearer()

ACCESS_TOKEN_EXPIRE_MINUTES = 30
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
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
):
    """Validate the Bearer token and return the authenticated User row."""
    from backend.app.models.user import User  # local import avoids circular dep

    token = credentials.credentials
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
