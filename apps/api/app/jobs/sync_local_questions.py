import asyncio
import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.services.local_questions import LocalQuestion, load_local_questions


@dataclass(frozen=True)
class SyncTarget:
    exam: str
    questions_table: str
    sync_runs_table: str


@dataclass
class SyncStats:
    scanned_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0


def get_sync_target(exam: str | None = None) -> SyncTarget:
    exam = (exam or settings.quiz_exam).strip().lower()
    targets = {
        "aif": SyncTarget("aif", "aif_questions", "aif_sync_runs"),
        "clf": SyncTarget("clf", "questions", "sync_runs"),
        "saa": SyncTarget("saa", "saa_questions", "saa_sync_runs"),
    }
    try:
        return targets[exam]
    except KeyError as exc:
        raise RuntimeError("QUIZ_EXAM must be 'aif', 'clf', or 'saa'") from exc


class SupabaseRestClient:
    def __init__(self, target: SyncTarget) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        self.base_url = settings.supabase_url.rstrip("/")
        self.target = target
        self.headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }

    async def latest_question_no(self) -> int:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/rest/v1/{self.target.questions_table}",
                headers=self.headers,
                params={
                    "select": "question_no",
                    "question_no": "not.is.null",
                    "order": "question_no.desc",
                    "limit": "1",
                },
            )
            response.raise_for_status()
            rows = response.json()
        return int(rows[0]["question_no"]) if rows else 0

    async def select_existing(self) -> dict[int, dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page_size = 1000
        async with httpx.AsyncClient(timeout=30) as client:
            offset = 0
            while True:
                response = await client.get(
                    f"{self.base_url}/rest/v1/{self.target.questions_table}",
                    headers=self.headers,
                    params={
                        "select": "id,question_no,content_hash,is_active",
                        "question_no": "not.is.null",
                        "order": "question_no.asc",
                        "limit": str(page_size),
                        "offset": str(offset),
                    },
                )
                response.raise_for_status()
                page = response.json()
                rows.extend(page)
                if len(page) < page_size:
                    break
                offset += page_size

        existing: dict[int, dict[str, Any]] = {}
        for row in rows:
            question_no = int(row["question_no"])
            if question_no in existing:
                raise ValueError(
                    f"Supabase {self.target.questions_table} 有重複的 Q{question_no}"
                )
            existing[question_no] = row
        return existing

    async def insert_sync_run(self) -> str | None:
        payload = {
            "source": "local_json",
            "source_sheet_id": "local-json",
            "source_sheet_name": "questions",
            "status": "running",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/rest/v1/{self.target.sync_runs_table}",
                headers={**self.headers, "Prefer": "return=representation"},
                json=payload,
            )
            response.raise_for_status()
            rows = response.json()
        return rows[0]["id"] if rows else None

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
                f"{self.base_url}/rest/v1/{self.target.sync_runs_table}",
                headers=self.headers,
                params={"id": f"eq.{sync_run_id}"},
                json=payload,
            )
            response.raise_for_status()

    async def insert_question(self, payload: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/rest/v1/{self.target.questions_table}",
                headers={**self.headers, "Prefer": "return=minimal"},
                json=payload,
            )
            if response.is_error:
                detail = response.text.strip() or response.reason_phrase
                raise RuntimeError(
                    f"Supabase insert failed for {self.target.exam.upper()} "
                    f"Q{payload.get('question_no')}: HTTP {response.status_code}: {detail}"
                )

    async def update_question(self, payload: dict[str, Any]) -> None:
        question_no = payload.get("question_no")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(
                f"{self.base_url}/rest/v1/{self.target.questions_table}",
                headers={**self.headers, "Prefer": "return=minimal"},
                params={"question_no": f"eq.{question_no}"},
                json=payload,
            )
            if response.is_error:
                detail = response.text.strip() or response.reason_phrase
                raise RuntimeError(
                    f"Supabase update failed for {self.target.exam.upper()} "
                    f"Q{question_no}: HTTP {response.status_code}: {detail}"
                )


def pending_questions(
    questions: list[LocalQuestion],
    latest_question_no: int,
) -> list[LocalQuestion]:
    pending = [item for item in questions if item.question_no > latest_question_no]
    if pending and pending[0].question_no != latest_question_no + 1:
        raise ValueError(
            f"Supabase 最新題號是 Q{latest_question_no}，但下一個本機題號是 "
            f"Q{pending[0].question_no}；請先補齊 Q{latest_question_no + 1}"
        )
    for previous, current in zip(pending, pending[1:]):
        if current.question_no != previous.question_no + 1:
            raise ValueError(
                f"本機題庫缺少 Q{previous.question_no + 1}，不可跳號增量同步"
            )
    return pending


async def sync_local_questions(exam: str | None = None) -> SyncStats:
    target = get_sync_target(exam)
    directory = Path(settings.questions_dir).expanduser().resolve()
    questions = load_local_questions(directory, target.exam)
    client = SupabaseRestClient(target)
    existing = await client.select_existing()
    latest = max(existing, default=0)
    local_latest = questions[-1].question_no
    if latest > local_latest:
        raise ValueError(
            f"Supabase 最新題號 Q{latest} 超過本機題庫最後一題 Q{local_latest}；"
            "questions 必須保留完整正式題庫，請先補齊本機 JSON"
        )
    new_questions: list[LocalQuestion] = []
    changed_questions: list[LocalQuestion] = []
    skipped_count = 0
    for item in questions:
        current = existing.get(item.question_no)
        if current is None:
            new_questions.append(item)
        elif current.get("content_hash") != item.payload.get("content_hash") or not current.get("is_active", False):
            changed_questions.append(item)
        else:
            skipped_count += 1

    if new_questions:
        pending_questions(new_questions, latest)
    stats = SyncStats(scanned_count=len(questions), skipped_count=skipped_count)
    sync_run_id = await client.insert_sync_run()

    try:
        for item in new_questions:
            await client.insert_question(item.payload)
            stats.inserted_count += 1
        for item in changed_questions:
            await client.update_question(item.payload)
            stats.updated_count += 1
        await client.finish_sync_run(sync_run_id, "success", stats)
        return stats
    except Exception as exc:
        await client.finish_sync_run(sync_run_id, "failed", stats, str(exc))
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="增量同步 questions 目錄中的 JSON 題庫")
    parser.add_argument(
        "--exam",
        choices=("aif", "clf", "saa"),
        help="要同步的考試題庫（未指定時使用 QUIZ_EXAM）",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="只驗證本機 JSON 並顯示最後題號，不連線 Supabase",
    )
    args = parser.parse_args()
    target = get_sync_target(args.exam)
    if args.validate_only:
        directory = Path(settings.questions_dir).expanduser().resolve()
        questions = load_local_questions(directory, target.exam)
        print(
            f"Local JSON validation completed for {target.exam}: "
            f"questions={len(questions)}, latest=Q{questions[-1].question_no}"
        )
        return

    stats = asyncio.run(sync_local_questions(args.exam))
    print(
        f"Local JSON sync completed for {target.exam}: "
        f"scanned={stats.scanned_count}, inserted={stats.inserted_count}, "
        f"updated={stats.updated_count}, "
        f"skipped={stats.skipped_count}"
    )


if __name__ == "__main__":
    main()
