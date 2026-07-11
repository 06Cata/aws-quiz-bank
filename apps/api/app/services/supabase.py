from datetime import UTC, datetime
import random

import httpx

from app.core.config import settings


def _service_headers() -> dict[str, str]:
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }


async def select_questions(limit: int | None = None) -> list[dict]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return []

    url = f"{settings.supabase_url}/rest/v1/questions"
    headers = _service_headers()
    params = {
        "select": "*",
        "is_active": "eq.true",
        "order": "question_no.asc",
    }
    if limit is not None:
        params["limit"] = str(limit)

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        questions = response.json()

    random.shuffle(questions)
    return questions


async def select_wrong_questions_for_user(user_id: str, limit: int | None = None) -> list[dict]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return []

    stats_url = f"{settings.supabase_url}/rest/v1/user_question_stats"
    questions_url = f"{settings.supabase_url}/rest/v1/questions"
    headers = _service_headers()
    stats_params = {
        "select": "question_id,total_attempts,wrong_count,updated_at",
        "user_id": f"eq.{user_id}",
        "wrong_count": "gt.0",
    }
    if limit is not None:
        stats_params["limit"] = str(max(limit * 5, 100))

    async with httpx.AsyncClient(timeout=20) as client:
        stats_response = await client.get(stats_url, headers=headers, params=stats_params)
        stats_response.raise_for_status()
        stats = stats_response.json()

        question_ids = [
            str(item.get("question_id"))
            for item in stats
            if item.get("question_id")
        ]
        if not question_ids:
            return []

        questions_response = await client.get(
            questions_url,
            headers=headers,
            params={
                "select": "*",
                "id": f"in.({','.join(question_ids)})",
                "is_active": "eq.true",
            },
        )
        questions_response.raise_for_status()
        questions = {
            item["id"]: item
            for item in questions_response.json()
            if item.get("id")
        }

    sorted_stats = sorted(
        stats,
        key=lambda item: (
            (int(item.get("wrong_count") or 0) / max(int(item.get("total_attempts") or 1), 1)),
            int(item.get("wrong_count") or 0),
            str(item.get("updated_at") or ""),
        ),
        reverse=True,
    )

    weighted_questions: list[dict] = []
    for item in sorted_stats:
        question_id = str(item.get("question_id") or "")
        question = questions.get(question_id)
        if not question:
            continue

        wrong_count = max(int(item.get("wrong_count") or 1), 1)
        total_attempts = max(int(item.get("total_attempts") or 1), 1)
        wrong_ratio = wrong_count / total_attempts
        repeat_count = min(max(round(wrong_ratio * 5), 1), 5)
        for _ in range(repeat_count):
            weighted_questions.append({
                **question,
                "review_wrong_count": wrong_count,
                "review_wrong_ratio": wrong_ratio,
            })

    questions_for_review = weighted_questions
    if limit is None:
        return questions_for_review

    return questions_for_review[:limit]


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


async def record_question_attempt(
    user_id: str,
    question_id: str,
    selected_options: list[str],
    is_correct: bool,
) -> dict:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase service role is not configured")

    now = datetime.now(UTC).isoformat()
    attempts_url = f"{settings.supabase_url}/rest/v1/question_attempts"
    stats_url = f"{settings.supabase_url}/rest/v1/user_question_stats"
    headers = {
        **_service_headers(),
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    attempt_payload = {
        "user_id": user_id,
        "question_id": question_id,
        "selected_options": selected_options,
        "is_correct": is_correct,
        "answered_at": now,
    }

    stats_params = {
        "select": "user_id,question_id,total_attempts,correct_count,wrong_count",
        "user_id": f"eq.{user_id}",
        "question_id": f"eq.{question_id}",
        "limit": "1",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        attempt_response = await client.post(attempts_url, headers=headers, json=attempt_payload)
        attempt_response.raise_for_status()
        attempt = attempt_response.json()

        existing_response = await client.get(stats_url, headers=_service_headers(), params=stats_params)
        existing_response.raise_for_status()
        existing = existing_response.json()

        if existing:
            current = existing[0]
            stats_payload = {
                "total_attempts": int(current.get("total_attempts") or 0) + 1,
                "correct_count": int(current.get("correct_count") or 0) + (1 if is_correct else 0),
                "wrong_count": int(current.get("wrong_count") or 0) + (0 if is_correct else 1),
                "last_answered_at": now,
                "updated_at": now,
            }
            if not is_correct:
                stats_payload["last_wrong_at"] = now

            stats_response = await client.patch(
                stats_url,
                headers=headers,
                params={"user_id": f"eq.{user_id}", "question_id": f"eq.{question_id}"},
                json=stats_payload,
            )
            stats_response.raise_for_status()
            stats = stats_response.json()
        else:
            stats_payload = {
                "user_id": user_id,
                "question_id": question_id,
                "total_attempts": 1,
                "correct_count": 1 if is_correct else 0,
                "wrong_count": 0 if is_correct else 1,
                "last_answered_at": now,
                "last_wrong_at": None if is_correct else now,
                "updated_at": now,
            }
            stats_response = await client.post(stats_url, headers=headers, json=stats_payload)
            stats_response.raise_for_status()
            stats = stats_response.json()

    return {
        "attempt": attempt[0] if attempt else attempt_payload,
        "stats": stats[0] if stats else stats_payload,
    }
