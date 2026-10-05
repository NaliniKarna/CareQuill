from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.db import get_db
from app.models.user import User
from app.services.auth_service import AuthService

_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Enforces authentication on any route that depends on it. Raises
    UnauthorizedError (-> 401) via AuthService for a missing/invalid/expired
    token, an inactive user, or a malformed subject claim."""
    auth_service = AuthService(session)
    return await auth_service.get_current_user(access_token=credentials.credentials)
