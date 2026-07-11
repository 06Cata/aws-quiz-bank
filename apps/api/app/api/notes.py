from fastapi import APIRouter, Header, HTTPException
from httpx import HTTPStatusError
from pydantic import BaseModel, Field

from app.services.supabase import get_auth_user, select_review_notes_for_user, upsert_review_note

router = APIRouter(prefix="/notes", tags=["notes"])


class ReviewNotePayload(BaseModel):
    question_id: str = Field(min_length=1)
    option_key: str = Field(pattern="^[A-Z]$")
    quiz_mode: str = Field(default="practice", pattern="^(practice|wrong|exam)$")


async def authenticated_user(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Supabase access token")

    access_token = authorization.split(" ", 1)[1].strip()
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing Supabase access token")

    try:
        user = await get_auth_user(access_token)
    except HTTPStatusError as exc:
        status_code = 401 if exc.response.status_code in {401, 403} else 502
        raise HTTPException(status_code=status_code, detail="Unable to verify Supabase user") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to verify Supabase user") from exc

    if not user.get("id"):
        raise HTTPException(status_code=401, detail="Unable to verify Supabase user")

    return user


@router.get("")
async def list_notes(authorization: str | None = Header(default=None)) -> dict:
    user = await authenticated_user(authorization)

    try:
        notes = await select_review_notes_for_user(user_id=user["id"])
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to load review notes") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load review notes") from exc

    return {"items": notes}


@router.post("")
async def save_note(
    payload: ReviewNotePayload,
    authorization: str | None = Header(default=None),
) -> dict:
    user = await authenticated_user(authorization)

    try:
        note = await upsert_review_note(
            user_id=user["id"],
            question_id=payload.question_id,
            option_key=payload.option_key,
            quiz_mode=payload.quiz_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to save review note") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save review note") from exc

    return {"note": note}
