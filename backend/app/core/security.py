"""Bearer token authentication dependency for FastAPI."""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

security_scheme = HTTPBearer(auto_error=False)


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> str:
    """Validate the Bearer token against the configured API key.

    Returns the token string on success, raises 401/403 on failure.
    If no API_BEARER_TOKEN is configured (empty), authentication is bypassed
    for local development convenience.
    """
    # Skip auth if no token is configured (dev mode)
    if not settings.API_BEARER_TOKEN:
        return "dev-mode"

    if credentials is None:
        logger.warning("Missing authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != settings.API_BEARER_TOKEN:
        logger.warning("Invalid bearer token attempt: %s", credentials.credentials)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired token",
        )

    return credentials.credentials
