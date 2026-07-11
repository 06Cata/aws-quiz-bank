from fastapi import APIRouter, Header, HTTPException
from httpx import HTTPStatusError

from app.services.supabase import ensure_profile_for_user, get_auth_user

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("/me")
async def ensure_my_profile(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Supabase access token")

    access_token = authorization.split(" ", 1)[1].strip()
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing Supabase access token")

    try:
        user = await get_auth_user(access_token)
        result = await ensure_profile_for_user(user)
    except HTTPStatusError as exc:
        status_code = 401 if exc.response.status_code in {401, 403} else 502
        raise HTTPException(status_code=status_code, detail="Unable to verify Supabase user") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to ensure profile") from exc

    return result
