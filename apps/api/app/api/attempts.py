from pydantic import BaseModel, Field
from fastapi import APIRouter, Header, HTTPException
from httpx import HTTPStatusError

from app.services.supabase import get_auth_user, record_question_attempt

router = APIRouter(prefix="/attempts", tags=["attempts"])


class AttemptPayload(BaseModel):
    question_id: str = Field(min_length=1)
    selected_options: list[str] = Field(min_length=1)
    is_correct: bool


@router.post("")
async def create_attempt(
    payload: AttemptPayload,
    authorization: str | None = Header(default=None),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Supabase access token")

    access_token = authorization.split(" ", 1)[1].strip()
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing Supabase access token")

    selected_options = [
        option.strip().upper()
        for option in payload.selected_options
        if option.strip()
    ]
    if not selected_options:
        raise HTTPException(status_code=422, detail="selected_options cannot be empty")

    try:
        user = await get_auth_user(access_token)
        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Unable to verify Supabase user")

        result = await record_question_attempt(
            user_id=user_id,
            question_id=payload.question_id,
            selected_options=selected_options,
            is_correct=payload.is_correct,
        )
    except HTTPException:
        raise
    except HTTPStatusError as exc:
        status_code = 401 if exc.response.status_code in {401, 403} else 502
        raise HTTPException(status_code=status_code, detail="Unable to record attempt") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to record attempt") from exc

    return result
