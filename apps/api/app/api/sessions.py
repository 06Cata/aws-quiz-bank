from fastapi import APIRouter, Header, HTTPException
from httpx import HTTPStatusError
from pydantic import BaseModel, Field

from app.services.supabase import create_quiz_session, finish_quiz_session, get_auth_user

router = APIRouter(prefix="/sessions", tags=["sessions"])


class SessionPayload(BaseModel):
    mode: str = Field(pattern="^(practice|wrong|exam)$")
    certification: str = Field(default="AWS Cloud Practitioner", min_length=1)
    question_count: int = Field(default=0, ge=0)


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


@router.post("")
async def create_session(
    payload: SessionPayload,
    authorization: str | None = Header(default=None),
) -> dict:
    user = await authenticated_user(authorization)

    try:
        session = await create_quiz_session(
            user_id=user["id"],
            mode=payload.mode,
            certification=payload.certification,
            question_count=payload.question_count,
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to create quiz session") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to create quiz session") from exc

    return {"session": session}


@router.patch("/{session_id}/finish")
async def finish_session(
    session_id: str,
    authorization: str | None = Header(default=None),
) -> dict:
    user = await authenticated_user(authorization)

    try:
        session = await finish_quiz_session(user_id=user["id"], session_id=session_id)
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to finish quiz session") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to finish quiz session") from exc

    return {"session": session}
