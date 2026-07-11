from fastapi import APIRouter, Header, HTTPException, Query
from httpx import HTTPStatusError

from app.services.supabase import get_auth_user, select_questions, select_wrong_questions_for_user

router = APIRouter(prefix="/questions", tags=["questions"])


async def authenticated_user(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Supabase access token")

    access_token = authorization.split(" ", 1)[1].strip()
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing Supabase access token")

    try:
        await get_auth_user(access_token)
    except HTTPStatusError as exc:
        status_code = 401 if exc.response.status_code in {401, 403} else 502
        raise HTTPException(status_code=status_code, detail="Unable to verify Supabase user") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to verify Supabase user") from exc


@router.get("/wrong")
async def list_wrong_questions(
    limit: int = Query(default=20, ge=1, le=100),
    authorization: str | None = Header(default=None),
) -> dict:
    user = await authenticated_user(authorization)
    questions = await select_wrong_questions_for_user(user_id=user["id"], limit=limit)
    return {"items": questions}


@router.get("")
async def list_questions(
    limit: int = Query(default=20, ge=1, le=100),
    authorization: str | None = Header(default=None),
) -> dict:
    await authenticated_user(authorization)
    questions = await select_questions(limit=limit)
    return {"items": questions}
