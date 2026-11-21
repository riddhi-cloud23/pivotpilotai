from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def require_user(credentials: Credentials) -> str:
    settings = get_settings()
    if not credentials:
        if settings.demo_mode:
            return "demo-user"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="A valid Supabase access token is required.")
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase token verification is not configured.")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.supabase_anon_key,
                    "Authorization": f"Bearer {credentials.credentials}",
                },
            )
        if response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The supplied access token is invalid or expired.")
        user_id = response.json().get("id")
        if not isinstance(user_id, str) or not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase did not return a valid user.")
        return user_id
    except httpx.HTTPError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not verify the session with Supabase Auth.") from error
