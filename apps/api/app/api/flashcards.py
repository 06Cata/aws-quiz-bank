from fastapi import APIRouter, Header, HTTPException
from httpx import HTTPStatusError
from pydantic import BaseModel, Field

from app.api.notes import authenticated_user
from app.services.supabase import (
    delete_flashcard_note_for_user,
    save_flashcard_note,
    select_flashcard_notes_for_user,
    select_flashcards,
)


clf_router = APIRouter(tags=["flashcards"])
saa_router = APIRouter(prefix="/saa", tags=["saa-flashcards"])


class FlashcardNotePayload(BaseModel):
    flashcard_id: str = Field(min_length=1)


def register_routes(router: APIRouter, exam: str) -> None:
    @router.get("/flashcards")
    async def list_flashcards() -> dict:
        try:
            return {"items": await select_flashcards(exam=exam)}
        except HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail="Unable to load flashcards") from exc

    @router.get("/flashcard-notes")
    async def list_flashcard_notes(authorization: str | None = Header(default=None)) -> dict:
        user = await authenticated_user(authorization)
        try:
            return {"items": await select_flashcard_notes_for_user(user["id"], exam=exam)}
        except HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail="Unable to load flashcard notes") from exc

    @router.post("/flashcard-notes")
    async def create_flashcard_note(
        payload: FlashcardNotePayload,
        authorization: str | None = Header(default=None),
    ) -> dict:
        user = await authenticated_user(authorization)
        try:
            return {"note": await save_flashcard_note(user["id"], payload.flashcard_id, exam=exam)}
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail="Unable to save flashcard note") from exc

    @router.delete("/flashcard-notes/{note_id}")
    async def delete_flashcard_note(
        note_id: str,
        authorization: str | None = Header(default=None),
    ) -> dict:
        user = await authenticated_user(authorization)
        try:
            deleted = await delete_flashcard_note_for_user(user["id"], note_id, exam=exam)
        except HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail="Unable to delete flashcard note") from exc
        if not deleted:
            raise HTTPException(status_code=404, detail="Flashcard note not found")
        return {"deleted": True}


register_routes(clf_router, "clf")
register_routes(saa_router, "saa")
