import httpx

from app.core.config import settings


async def select_questions(limit: int = 20) -> list[dict]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return []

    url = f"{settings.supabase_url}/rest/v1/questions"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    params = {
        "select": "*",
        "is_active": "eq.true",
        "order": "question_no.asc",
        "limit": str(limit),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
