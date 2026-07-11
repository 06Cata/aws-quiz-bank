from datetime import UTC, datetime
import random

import httpx

from app.core.config import settings

EXAM_DOMAIN_WEIGHTS = {
    "domain_1": 0.24,
    "domain_2": 0.30,
    "domain_3": 0.34,
    "domain_4": 0.12,
}


def _empty_localized_text() -> dict[str, str]:
    return {"zh": "", "en": ""}


def _localized_text(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return _empty_localized_text()

    return {
        "zh": str(value.get("zh") or "").strip(),
        "en": str(value.get("en") or "").strip(),
    }


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


def _exam_domain_key(question: dict) -> str | None:
    exam_domain = str(question.get("exam_domain") or "").lower()
    if "領域 1" in exam_domain or "domain 1" in exam_domain or "cloud concepts" in exam_domain:
        return "domain_1"
    if "領域 2" in exam_domain or "domain 2" in exam_domain or "security and compliance" in exam_domain:
        return "domain_2"
    if "領域 3" in exam_domain or "domain 3" in exam_domain or "cloud technology and services" in exam_domain:
        return "domain_3"
    if "領域 4" in exam_domain or "domain 4" in exam_domain or "billing" in exam_domain:
        return "domain_4"
    return None


def _domain_quotas(total_count: int) -> dict[str, int]:
    base_quotas = {
        domain: int(total_count * weight)
        for domain, weight in EXAM_DOMAIN_WEIGHTS.items()
    }
    remaining = total_count - sum(base_quotas.values())
    remainders = sorted(
        EXAM_DOMAIN_WEIGHTS,
        key=lambda domain: (total_count * EXAM_DOMAIN_WEIGHTS[domain]) - base_quotas[domain],
        reverse=True,
    )

    for domain in remainders[:remaining]:
        base_quotas[domain] += 1

    return base_quotas


def _weighted_sample_without_replacement(
    candidates: list[tuple[dict, float]],
    target_count: int,
) -> list[dict]:
    pool = [
        (question, max(score, 0.01))
        for question, score in candidates
    ]
    selected_questions: list[dict] = []

    while pool and len(selected_questions) < target_count:
        total_weight = sum(score for _, score in pool)
        pick = random.uniform(0, total_weight)
        cumulative_weight = 0.0

        for index, (question, score) in enumerate(pool):
            cumulative_weight += score
            if pick <= cumulative_weight:
                selected_questions.append(question)
                pool.pop(index)
                break

    return selected_questions


async def select_exam_questions(limit: int | None = None) -> list[dict]:
    questions = await select_questions()
    if not questions:
        return []

    target_count = min(limit or len(questions), len(questions))
    grouped_questions: dict[str, list[dict]] = {domain: [] for domain in EXAM_DOMAIN_WEIGHTS}
    unmatched_questions: list[dict] = []

    for question in questions:
        domain = _exam_domain_key(question)
        if domain:
            grouped_questions[domain].append(question)
        else:
            unmatched_questions.append(question)

    for domain_questions in grouped_questions.values():
        random.shuffle(domain_questions)
    random.shuffle(unmatched_questions)

    selected_questions: list[dict] = []
    selected_ids: set[str] = set()
    quotas = _domain_quotas(target_count)

    for domain in EXAM_DOMAIN_WEIGHTS:
        for question in grouped_questions[domain][:quotas[domain]]:
            question_id = str(question.get("id") or "")
            if question_id and question_id not in selected_ids:
                selected_questions.append(question)
                selected_ids.add(question_id)

    remaining_pool = [
        question
        for domain_questions in grouped_questions.values()
        for question in domain_questions
        if str(question.get("id") or "") not in selected_ids
    ]
    remaining_pool.extend(
        question
        for question in unmatched_questions
        if str(question.get("id") or "") not in selected_ids
    )
    random.shuffle(remaining_pool)

    for question in remaining_pool:
        if len(selected_questions) >= target_count:
            break

        question_id = str(question.get("id") or "")
        if question_id and question_id not in selected_ids:
            selected_questions.append(question)
            selected_ids.add(question_id)

    random.shuffle(selected_questions)
    return selected_questions


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

    max_wrong_count = max(
        (int(item.get("wrong_count") or 0) for item in stats),
        default=1,
    )
    weighted_candidates: list[tuple[dict, float]] = []

    for item in stats:
        question_id = str(item.get("question_id") or "")
        question = questions.get(question_id)
        if not question:
            continue

        wrong_count = max(int(item.get("wrong_count") or 1), 1)
        total_attempts = max(int(item.get("total_attempts") or 1), 1)
        wrong_ratio = wrong_count / total_attempts
        normalized_wrong_count = wrong_count / max(max_wrong_count, 1)
        review_score = (wrong_ratio * 0.7) + (normalized_wrong_count * 0.3)
        weighted_candidates.append(({
            **question,
            "review_wrong_count": wrong_count,
            "review_wrong_ratio": wrong_ratio,
            "review_score": review_score,
        }, review_score))

    target_count = min(limit or len(weighted_candidates), len(weighted_candidates))
    return _weighted_sample_without_replacement(weighted_candidates, target_count)



async def upsert_review_note(
    user_id: str,
    question_id: str,
    option_key: str,
    quiz_mode: str,
) -> dict:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase service role is not configured")

    option_key = option_key.strip().upper()
    questions_url = f"{settings.supabase_url}/rest/v1/questions"
    notes_url = f"{settings.supabase_url}/rest/v1/review_notes"
    headers = {
        **_service_headers(),
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        question_response = await client.get(
            questions_url,
            headers=_service_headers(),
            params={
                "select": "id,question_no,exam_domain,question_text,options,option_explanations,correct_options",
                "id": f"eq.{question_id}",
                "is_active": "eq.true",
                "limit": "1",
            },
        )
        question_response.raise_for_status()
        questions = question_response.json()
        if not questions:
            raise ValueError("Question not found")

        question = questions[0]
        options = question.get("options") if isinstance(question.get("options"), dict) else {}
        explanations = (
            question.get("option_explanations")
            if isinstance(question.get("option_explanations"), dict)
            else {}
        )
        option_text = _localized_text(options.get(option_key))
        explanation_text = _localized_text(explanations.get(option_key))

        note_payload = {
            "user_id": user_id,
            "question_id": question_id,
            "option_key": option_key,
            "quiz_mode": quiz_mode,
            "question_no": question.get("question_no"),
            "exam_domain": question.get("exam_domain"),
            "question_text": _localized_text(question.get("question_text")),
            "option_text": option_text,
            "explanation_text": explanation_text,
            "correct_options": question.get("correct_options") or [],
            "updated_at": datetime.now(UTC).isoformat(),
        }

        note_response = await client.post(
            notes_url,
            headers=headers,
            params={"on_conflict": "user_id,question_id,option_key"},
            json=note_payload,
        )
        note_response.raise_for_status()
        notes = note_response.json()

    return notes[0] if notes else note_payload


async def select_review_notes_for_user(user_id: str) -> list[dict]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return []

    url = f"{settings.supabase_url}/rest/v1/review_notes"
    params = {
        "select": "*",
        "user_id": f"eq.{user_id}",
        "order": "updated_at.desc",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, headers=_service_headers(), params=params)
        response.raise_for_status()
        return response.json()


async def delete_review_note_for_user(user_id: str, note_id: str) -> bool:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase service role is not configured")

    url = f"{settings.supabase_url}/rest/v1/review_notes"
    headers = {
        **_service_headers(),
        "Prefer": "return=representation",
    }
    params = {
        "id": f"eq.{note_id}",
        "user_id": f"eq.{user_id}",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.delete(url, headers=headers, params=params)
        response.raise_for_status()
        deleted_notes = response.json()

    return bool(deleted_notes)


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


async def create_quiz_session(
    user_id: str,
    mode: str,
    certification: str,
    question_count: int,
) -> dict:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase service role is not configured")

    url = f"{settings.supabase_url}/rest/v1/quiz_sessions"
    headers = {
        **_service_headers(),
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    payload = {
        "user_id": user_id,
        "mode": mode,
        "certification": certification,
        "question_count": question_count,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        session = response.json()

    return session[0] if session else payload


async def finish_quiz_session(user_id: str, session_id: str) -> dict:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase service role is not configured")

    url = f"{settings.supabase_url}/rest/v1/quiz_sessions"
    headers = {
        **_service_headers(),
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    payload = {"finished_at": datetime.now(UTC).isoformat()}

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.patch(
            url,
            headers=headers,
            params={"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"},
            json=payload,
        )
        response.raise_for_status()
        session = response.json()

    return session[0] if session else {"id": session_id, **payload}


async def record_question_attempt(
    user_id: str,
    question_id: str,
    selected_options: list[str],
    is_correct: bool,
    session_id: str | None = None,
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
    if session_id:
        attempt_payload["session_id"] = session_id

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
