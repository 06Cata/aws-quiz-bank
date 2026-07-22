import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.services.local_flashcards import LocalFlashcard, load_local_flashcards


@dataclass(frozen=True)
class SyncTarget:
    exam: str
    flashcards_table: str


@dataclass
class SyncStats:
    scanned_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    deactivated_count: int = 0


def get_sync_target(exam: str | None = None) -> SyncTarget:
    normalized_exam = (exam or settings.quiz_exam).strip().lower()
    targets = {
        "clf": SyncTarget("clf", "clf_flashcards"),
        "saa": SyncTarget("saa", "saa_flashcards"),
    }
    try:
        return targets[normalized_exam]
    except KeyError as exc:
        raise RuntimeError("QUIZ_EXAM must be either 'clf' or 'saa'") from exc


class SupabaseFlashcardClient:
    def __init__(self, target: SyncTarget) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        self.base_url = settings.supabase_url.rstrip("/")
        self.target = target
        self.url = f"{self.base_url}/rest/v1/{target.flashcards_table}"
        self.headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }

    async def select_existing(self) -> dict[str, dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page_size = 1000
        async with httpx.AsyncClient(timeout=30) as client:
            offset = 0
            while True:
                response = await client.get(
                    self.url,
                    headers=self.headers,
                    params={
                        "select": "id,source_key,content_hash,is_active",
                        "order": "source_key.asc",
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
        return {
            str(row["source_key"]): row
            for row in rows
            if row.get("source_key")
        }

    async def upsert_cards(self, cards: list[LocalFlashcard]) -> None:
        if not cards:
            return
        updated_at = datetime.now(UTC).isoformat()
        payload = [{**card.payload, "updated_at": updated_at} for card in cards]
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self.url,
                headers={
                    **self.headers,
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                params={"on_conflict": "source_key"},
                json=payload,
            )
            if response.is_error:
                detail = response.text.strip() or response.reason_phrase
                raise RuntimeError(
                    f"Supabase upsert failed for {self.target.exam.upper()} flashcards: "
                    f"HTTP {response.status_code}: {detail}"
                )

    async def deactivate_cards(self, source_keys: list[str]) -> None:
        if not source_keys:
            return
        updated_at = datetime.now(UTC).isoformat()
        batch_size = 100
        async with httpx.AsyncClient(timeout=30) as client:
            for start in range(0, len(source_keys), batch_size):
                batch = source_keys[start:start + batch_size]
                response = await client.patch(
                    self.url,
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"source_key": f"in.({','.join(batch)})"},
                    json={"is_active": False, "updated_at": updated_at},
                )
                if response.is_error:
                    detail = response.text.strip() or response.reason_phrase
                    raise RuntimeError(
                        f"Supabase deactivate failed for {self.target.exam.upper()} flashcards: "
                        f"HTTP {response.status_code}: {detail}"
                    )


async def sync_local_flashcards(exam: str | None = None) -> SyncStats:
    target = get_sync_target(exam)
    directory = Path(settings.flashcards_dir).expanduser().resolve()
    cards = load_local_flashcards(directory, target.exam)
    client = SupabaseFlashcardClient(target)
    existing = await client.select_existing()

    new_cards: list[LocalFlashcard] = []
    changed_cards: list[LocalFlashcard] = []
    skipped_count = 0
    local_source_keys = {card.source_key for card in cards}

    for card in cards:
        current = existing.get(card.source_key)
        if current is None:
            new_cards.append(card)
        elif current.get("content_hash") != card.content_hash or not current.get("is_active", False):
            changed_cards.append(card)
        else:
            skipped_count += 1

    removed_source_keys = [
        source_key
        for source_key, row in existing.items()
        if source_key not in local_source_keys and row.get("is_active", False)
    ]

    await client.upsert_cards([*new_cards, *changed_cards])
    await client.deactivate_cards(removed_source_keys)
    return SyncStats(
        scanned_count=len(cards),
        inserted_count=len(new_cards),
        updated_count=len(changed_cards),
        skipped_count=skipped_count,
        deactivated_count=len(removed_source_keys),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="驗證並同步 flashcards 目錄中的卡牌 JSON")
    parser.add_argument(
        "--exam",
        choices=("clf", "saa"),
        help="要驗證或同步的考試卡牌（未指定時使用 QUIZ_EXAM）",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="只驗證本機 JSON，不連線或修改 Supabase",
    )
    args = parser.parse_args()
    target = get_sync_target(args.exam)
    directory = Path(settings.flashcards_dir).expanduser().resolve()

    if args.validate_only:
        cards = load_local_flashcards(directory, target.exam)
        chapter_count = len({card.chapter_key for card in cards})
        print(
            f"Local flashcard validation completed for {target.exam}: "
            f"chapters={chapter_count}, cards={len(cards)}"
        )
        return

    stats = asyncio.run(sync_local_flashcards(target.exam))
    print(
        f"Local flashcard sync completed for {target.exam}: "
        f"scanned={stats.scanned_count}, inserted={stats.inserted_count}, "
        f"updated={stats.updated_count}, skipped={stats.skipped_count}, "
        f"deactivated={stats.deactivated_count}"
    )


if __name__ == "__main__":
    main()
