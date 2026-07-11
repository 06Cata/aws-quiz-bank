import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.services.google_sheet import fetch_sheet_rows


SHEET_ID = settings.google_sheet_id
SHEET_NAME = settings.google_sheet_name

QUESTION_ALIASES = ("題目", "Question", "question", "question_text", "題目 (Question)")
DOMAIN_ALIASES = ("考試領域", "Exam Domain", "exam_domain", "領域")
QUESTION_NO_ALIASES = ("題號", "Question No", "question_no", "No", "編號")
OPTIONS_ALIASES = ("選項", "Options", "options", "選項 (Options)")
EXPLANATIONS_ALIASES = (
    "各選項解析",
    "各選項解析 (Analysis)",
    "Analysis",
    "analysis",
    "option_explanations",
)
CHOICE_TYPE_ALIASES = (
    "單選或複選",
    "單選或複選 (Single or multiple)",
    "Single or multiple",
    "choice_type",
)
ANSWER_ALIASES = ("正確答案", "正確答案 (Answer)", "Answer", "answer", "correct_options")
DISCUSSION_ALIASES = ("社群討論", "社群討論 (Discussion)", "Discussion", "discussion")


@dataclass
class SyncStats:
    scanned_count: int = 0
    inserted_count: int = 0
    skipped_count: int = 0


def pick(row: dict[str, str], aliases: tuple[str, ...]) -> str:
    normalized = {key.strip().lower(): value for key, value in row.items()}

    for alias in aliases:
        value = normalized.get(alias.strip().lower())
        if value:
            return value

    for key, value in row.items():
        compact_key = re.sub(r"\s+", "", key).lower()
        for alias in aliases:
            compact_alias = re.sub(r"\s+", "", alias).lower()
            if compact_alias in compact_key and value:
                return value

    return ""


def parse_jsonish(value: str) -> Any:
    if not value:
        return {}

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def bilingual(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        zh = (
            value.get("zh")
            or value.get("ZH")
            or value.get("繁體中文")
            or value.get("中文")
            or value.get("Traditional Chinese")
            or ""
        )
        en = value.get("en") or value.get("ENGLISH") or value.get("English") or value.get("英文") or ""
        return {"zh": str(zh), "en": str(en)}

    return {"zh": str(value), "en": ""}


def pick_language_map(value: dict[str, Any], aliases: tuple[str, ...]) -> dict[str, Any]:
    normalized = {str(key).strip().lower(): item for key, item in value.items()}
    for alias in aliases:
        item = normalized.get(alias.strip().lower())
        if isinstance(item, dict):
            return item
    return {}


def bilingual_option_map(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        return {}

    zh_map = pick_language_map(value, ("zh", "繁體中文", "中文", "traditional chinese"))
    en_map = pick_language_map(value, ("en", "english", "英文"))
    if zh_map or en_map:
        option_keys = sorted({str(key).strip().upper() for key in zh_map.keys() | en_map.keys() if str(key).strip()})
        return {
            option_key: {
                "zh": str(zh_map.get(option_key) or zh_map.get(option_key.lower()) or ""),
                "en": str(en_map.get(option_key) or en_map.get(option_key.lower()) or ""),
            }
            for option_key in option_keys
        }

    result: dict[str, dict[str, str]] = {}
    for key, option_value in value.items():
        option_key = str(key).strip().upper()
        if option_key:
            result[option_key] = bilingual(option_value)
    return result


def parse_choice_type(value: str) -> str:
    lowered = value.strip().lower()
    if "複" in value or "multiple" in lowered:
        return "multiple"
    return "single"


def extract_correct_options(answer_value: Any) -> list[str]:
    text = ""
    if isinstance(answer_value, list):
        return [str(item).strip().upper() for item in answer_value if str(item).strip()]
    if isinstance(answer_value, dict):
        text = " ".join(str(value) for value in answer_value.values())
    else:
        text = str(answer_value)

    matches = re.findall(r"\b[A-F]\b", text.upper())
    return list(dict.fromkeys(matches))


def int_or_none(value: str) -> int | None:
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def content_hash(payload: dict[str, Any]) -> str:
    stable = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def build_question_payload(row: dict[str, str], row_number: int) -> dict[str, Any] | None:
    question_raw = pick(row, QUESTION_ALIASES)
    options_raw = pick(row, OPTIONS_ALIASES)
    answer_raw = pick(row, ANSWER_ALIASES)

    if not question_raw or not options_raw or not answer_raw:
        return None

    question_text = bilingual(parse_jsonish(question_raw))
    options = bilingual_option_map(parse_jsonish(options_raw))
    option_explanations = bilingual_option_map(parse_jsonish(pick(row, EXPLANATIONS_ALIASES)))
    answer_json = parse_jsonish(answer_raw)
    correct_options = extract_correct_options(answer_json)

    if not question_text["zh"] and not question_text["en"]:
        return None
    if not options or not correct_options:
        return None

    hash_source = {
        "question_text": question_text,
        "options": options,
        "correct_options": correct_options,
    }

    return {
        "source": "google_sheet",
        "source_sheet_id": SHEET_ID,
        "source_sheet_name": SHEET_NAME,
        "source_row_number": row_number,
        "content_hash": content_hash(hash_source),
        "certification": "AWS Cloud Practitioner",
        "question_no": int_or_none(pick(row, QUESTION_NO_ALIASES)),
        "exam_domain": pick(row, DOMAIN_ALIASES) or None,
        "question_text": question_text,
        "options": options,
        "option_explanations": option_explanations,
        "correct_options": correct_options,
        "answer_text": bilingual(answer_json),
        "choice_type": parse_choice_type(pick(row, CHOICE_TYPE_ALIASES)),
        "discussion": bilingual(parse_jsonish(pick(row, DISCUSSION_ALIASES))),
        "is_active": True,
    }


class SupabaseRestClient:
    def __init__(self) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

        self.base_url = settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }

    async def insert_sync_run(self) -> str | None:
        payload = {
            "source": "google_sheet",
            "source_sheet_id": SHEET_ID,
            "source_sheet_name": SHEET_NAME,
            "status": "running",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/rest/v1/sync_runs",
                headers={**self.headers, "Prefer": "return=representation"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data[0]["id"] if data else None

    async def finish_sync_run(
        self,
        sync_run_id: str | None,
        status: str,
        stats: SyncStats,
        error_message: str | None = None,
    ) -> None:
        if not sync_run_id:
            return

        payload = {
            "status": status,
            "scanned_count": stats.scanned_count,
            "inserted_count": stats.inserted_count,
            "skipped_count": stats.skipped_count,
            "error_message": error_message,
            "finished_at": datetime.now(UTC).isoformat(),
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(
                f"{self.base_url}/rest/v1/sync_runs",
                headers=self.headers,
                params={"id": f"eq.{sync_run_id}"},
                json=payload,
            )
            response.raise_for_status()

    async def question_exists(self, question_hash: str) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/rest/v1/questions",
                headers=self.headers,
                params={"select": "id", "content_hash": f"eq.{question_hash}", "limit": "1"},
            )
            response.raise_for_status()
            return bool(response.json())

    async def insert_question(self, payload: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/rest/v1/questions",
                headers={**self.headers, "Prefer": "return=minimal"},
                json=payload,
            )
            response.raise_for_status()


async def sync_google_sheet() -> SyncStats:
    client = SupabaseRestClient()
    stats = SyncStats()
    sync_run_id = await client.insert_sync_run()

    try:
        rows = await fetch_sheet_rows(SHEET_ID, SHEET_NAME)

        for index, row in enumerate(rows, start=2):
            stats.scanned_count += 1
            payload = build_question_payload(row, index)
            if not payload:
                stats.skipped_count += 1
                continue

            if await client.question_exists(payload["content_hash"]):
                stats.skipped_count += 1
                continue

            await client.insert_question(payload)
            stats.inserted_count += 1

        await client.finish_sync_run(sync_run_id, "success", stats)
        return stats
    except Exception as exc:
        await client.finish_sync_run(sync_run_id, "failed", stats, str(exc))
        raise


def main() -> None:
    stats = asyncio.run(sync_google_sheet())
    print(
        "Google Sheet sync completed: "
        f"scanned={stats.scanned_count}, "
        f"inserted={stats.inserted_count}, "
        f"skipped={stats.skipped_count}"
    )


if __name__ == "__main__":
    main()
