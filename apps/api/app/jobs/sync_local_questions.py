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
    skipped_count: int = 0


def get_sync_target() -> SyncTarget:
    exam = settings.quiz_exam.strip().lower()
    targets = {
        "clf": SyncTarget("clf", "questions", "sync_runs"),
        "saa": SyncTarget("saa", "saa_questions", "saa_sync_runs"),
    }
    try:
        return targets[exam]
    except KeyError as exc:
        raise RuntimeError("QUIZ_EXAM must be either 'clf' or 'saa'") from exc


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
            response.raise_for_status()


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


async def sync_local_questions() -> SyncStats:
    target = get_sync_target()
    directory = Path(settings.questions_dir).expanduser().resolve()
    questions = load_local_questions(directory, target.exam)
    client = SupabaseRestClient(target)
    latest = await client.latest_question_no()
    local_latest = questions[-1].question_no
    if latest > local_latest:
        raise ValueError(
            f"Supabase 最新題號 Q{latest} 超過本機題庫最後一題 Q{local_latest}；"
            "questions 必須保留完整正式題庫，請先補齊本機 JSON"
        )
    pending = pending_questions(questions, latest)
    stats = SyncStats(
        scanned_count=len(questions),
        skipped_count=len(questions) - len(pending),
    )
    sync_run_id = await client.insert_sync_run()

    try:
        for item in pending:
            await client.insert_question(item.payload)
            stats.inserted_count += 1
        await client.finish_sync_run(sync_run_id, "success", stats)
        return stats
    except Exception as exc:
        await client.finish_sync_run(sync_run_id, "failed", stats, str(exc))
        raise


def main() -> None:
    target = get_sync_target()
    parser = argparse.ArgumentParser(description="增量同步 questions 目錄中的 JSON 題庫")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="只驗證本機 JSON 並顯示最後題號，不連線 Supabase",
    )
    args = parser.parse_args()
    if args.validate_only:
        directory = Path(settings.questions_dir).expanduser().resolve()
        questions = load_local_questions(directory, target.exam)
        print(
            f"Local JSON validation completed for {target.exam}: "
            f"questions={len(questions)}, latest=Q{questions[-1].question_no}"
        )
        return

    stats = asyncio.run(sync_local_questions())
    print(
        f"Local JSON sync completed for {target.exam}: "
        f"scanned={stats.scanned_count}, inserted={stats.inserted_count}, "
        f"skipped={stats.skipped_count}"
    )


if __name__ == "__main__":
    main()
