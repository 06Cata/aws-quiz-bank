from datetime import UTC, datetime

import httpx

from app.core.config import settings


def _service_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }


async def select_questions(limit: int = 20) -> list[dict]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return []

    url = f"{settings.supabase_url}/rest/v1/questions"
    headers = _service_headers()
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


async def get_auth_user(access_token: str) -> dict:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase service role is not configured")

    url = f"{settings.supabase_url}/auth/v1/user"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {access_token}",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


async def ensure_profile_for_user(user: dict) -> dict:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase service role is not configured")

    user_id = user.get("id")
    if not user_id:
        raise ValueError("Auth user id is missing")

    metadata = user.get("user_metadata") or {}
    now = datetime.now(UTC).isoformat()
    profile_payload = {
        "id": user_id,
        "email": user.get("email") or "",
        "display_name": metadata.get("full_name") or metadata.get("name"),
        "avatar_url": metadata.get("avatar_url") or metadata.get("picture"),
        "last_seen_at": now,
    }

    url = f"{settings.supabase_url}/rest/v1/profiles"
    headers = {
        **_service_headers(),
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    select_params = {"select": "id,email,display_name,avatar_url,last_seen_at", "id": f"eq.{user_id}"}

    async with httpx.AsyncClient(timeout=20) as client:
        existing_response = await client.get(url, headers=_service_headers(), params=select_params)
        existing_response.raise_for_status()
        existing = existing_response.json()

        if existing:
            update_payload = {
                key: value
                for key, value in profile_payload.items()
                if key not in {"id", "last_seen_at"} and value is not None
            }
            update_payload["last_seen_at"] = now
            update_response = await client.patch(
                url,
                headers=headers,
                params={"id": f"eq.{user_id}"},
                json=update_payload,
            )
            update_response.raise_for_status()
            updated = update_response.json()
            return {"created": False, "profile": updated[0] if updated else existing[0]}

        insert_response = await client.post(url, headers=headers, json=profile_payload)
        if insert_response.status_code == 409:
            conflict_response = await client.get(url, headers=_service_headers(), params=select_params)
            conflict_response.raise_for_status()
            conflict_existing = conflict_response.json()
            return {
                "created": False,
                "profile": conflict_existing[0] if conflict_existing else profile_payload,
            }

        insert_response.raise_for_status()
        created = insert_response.json()
        return {"created": True, "profile": created[0] if created else profile_payload}
