from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from supabase import Client, create_client

from .config import Settings, get_settings

security = HTTPBearer()


class AuthenticatedUser(BaseModel):
    """Authenticated user information extracted from JWT."""

    id: str
    email: str | None = None
    role: str = "authenticated"


def get_supabase_client(settings: Annotated[Settings, Depends(get_settings)]) -> Client:
    """Get Supabase client with service key for admin operations."""
    return create_client(settings.supabase_url, settings.supabase_service_key)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Validate JWT and extract user information.

    Raises HTTPException 401 if token is invalid or expired.
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthenticatedUser(
            id=user_id,
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Type aliases for dependency injection
SupabaseClient = Annotated[Client, Depends(get_supabase_client)]
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
