from fastapi import APIRouter, Query

from app.services.supabase import select_questions

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get("")
async def list_questions(limit: int = Query(default=20, ge=1, le=100)) -> dict:
    questions = await select_questions(limit=limit)
    return {"items": questions}
