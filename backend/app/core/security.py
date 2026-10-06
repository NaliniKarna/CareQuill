"""
Password hashing and JWT access/refresh token utilities.

Password hashing uses Argon2 (via passlib), the current OWASP-recommended
default. Refresh tokens are stored server-side only as a hash (see
`RefreshToken` model + `refresh_token_repository`), never in plaintext, so a
leaked database dump does not hand out usable tokens.
"""
import asyncio
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

TokenType = Literal["access", "refresh"]


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


# Argon2 is deliberately CPU-expensive (tens to hundreds of milliseconds).
# Calling it directly inside an `async def` blocks the whole event loop, so
# EVERY other in-flight request stalls while one user logs in. The async
# variants below run it in a worker thread; services must use these.
async def hash_password_async(plain_password: str) -> str:
    return await asyncio.to_thread(hash_password, plain_password)


async def verify_password_async(plain_password: str, password_hash: str) -> bool:
    return await asyncio.to_thread(verify_password, plain_password, password_hash)


# A real Argon2 hash of a random value, computed once at import. Login
# verifies against it when the email is unknown so "no such account" and
# "wrong password" take the same time (prevents account enumeration by
# response timing).
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


async def verify_dummy_password_async(plain_password: str) -> None:
    await asyncio.to_thread(verify_password, plain_password, _DUMMY_PASSWORD_HASH)


# --------------------------------------------------------------------------
# JWT access tokens
# --------------------------------------------------------------------------
def create_access_token(user_id: uuid.UUID, extra_claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Raises jose.JWTError if the token is invalid or expired."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def try_decode_token(token: str) -> dict[str, Any] | None:
    try:
        return decode_token(token)
    except JWTError:
        return None


# --------------------------------------------------------------------------
# Opaque refresh tokens (random string, only a hash is persisted)
# --------------------------------------------------------------------------
def generate_opaque_token() -> str:
    """A high-entropy, URL-safe random token used for refresh tokens,
    password reset tokens and email verification tokens."""
    return secrets.token_urlsafe(48)


def hash_opaque_token(token: str) -> str:
    """Deterministic hash so we can look the token up by its hash without
    storing the plaintext. Not a password (already high entropy), so a fast
    hash (SHA-256) is appropriate and lets us index/query by hash."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
