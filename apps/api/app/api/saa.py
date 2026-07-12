from fastapi import APIRouter, Header, HTTPException, Query
from httpx import HTTPStatusError
from pydantic import BaseModel, Field

from app.services.supabase import (
    create_quiz_session,
    delete_review_note_for_user,
    finish_quiz_session,
    get_auth_user,
    record_question_attempt,
    select_exam_questions,
    select_questions,
    select_review_notes_for_user,
    select_wrong_questions_for_user,
    upsert_review_note,
)

router = APIRouter(prefix="/saa", tags=["saa"])


class AttemptPayload(BaseModel):
    session_id: str | None = None
    question_id: str = Field(min_length=1)
    selected_options: list[str] = Field(min_length=1)
    is_correct: bool


class SessionPayload(BaseModel):
    mode: str = Field(pattern="^(practice|wrong|exam)$")
    certification: str = Field(default="AWS Solutions Architect Associate", min_length=1)
    question_count: int = Field(default=0, ge=0)


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


@router.get("/questions/wrong")
async def list_wrong_questions(
    limit: int | None = Query(default=None, ge=1),
    authorization: str | None = Header(default=None),
) -> dict:
    user = await authenticated_user(authorization)
    questions = await select_wrong_questions_for_user(user_id=user["id"], limit=limit, exam="saa")
    return {"items": questions}


@router.get("/questions/exam")
async def list_exam_questions(
    limit: int = Query(default=65, ge=1),
    authorization: str | None = Header(default=None),
) -> dict:
    await authenticated_user(authorization)
    return {"items": await select_exam_questions(limit=limit, exam="saa")}


@router.get("/questions")
async def list_questions(
    limit: int | None = Query(default=None, ge=1),
    authorization: str | None = Header(default=None),
) -> dict:
    await authenticated_user(authorization)
    return {"items": await select_questions(limit=limit, exam="saa")}


@router.post("/attempts")
async def create_attempt(
    payload: AttemptPayload,
    authorization: str | None = Header(default=None),
) -> dict:
    user = await authenticated_user(authorization)
    selected_options = [option.strip().upper() for option in payload.selected_options if option.strip()]
    if not selected_options:
        raise HTTPException(status_code=422, detail="selected_options cannot be empty")

    try:
        return await record_question_attempt(
            user_id=user["id"],
            question_id=payload.question_id,
            selected_options=selected_options,
            is_correct=payload.is_correct,
            session_id=payload.session_id,
            exam="saa",
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to record SAA attempt") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to record SAA attempt") from exc


@router.post("/sessions")
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
            exam="saa",
        )
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to create SAA quiz session") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to create SAA quiz session") from exc
    return {"session": session}


@router.patch("/sessions/{session_id}/finish")
async def finish_session(
    session_id: str,
    authorization: str | None = Header(default=None),
) -> dict:
    user = await authenticated_user(authorization)
    try:
        session = await finish_quiz_session(user_id=user["id"], session_id=session_id, exam="saa")
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to finish SAA quiz session") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to finish SAA quiz session") from exc
    return {"session": session}


@router.get("/notes")
async def list_notes(authorization: str | None = Header(default=None)) -> dict:
    user = await authenticated_user(authorization)
    try:
        return {"items": await select_review_notes_for_user(user_id=user["id"], exam="saa")}
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to load SAA review notes") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to load SAA review notes") from exc


@router.post("/notes")
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
            exam="saa",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to save SAA review note") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to save SAA review note") from exc
    return {"note": note}


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    authorization: str | None = Header(default=None),
) -> dict:
    user = await authenticated_user(authorization)
    try:
        is_deleted = await delete_review_note_for_user(user_id=user["id"], note_id=note_id, exam="saa")
    except HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="Unable to delete SAA review note") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to delete SAA review note") from exc

    if not is_deleted:
        raise HTTPException(status_code=404, detail="SAA review note not found")
    return {"deleted": True}
