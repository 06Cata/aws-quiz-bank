import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXAMS = {"clf", "saa"}
CHAPTER_PATTERN = re.compile(r"^chapter(?P<order>[1-9]\d*)\s*:\s*(?P<label>.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class LocalFlashcard:
    source_key: str
    chapter_key: str
    chapter_order: int
    topic: str
    title: str
    exam_domain: str
    description: str
    content_hash: str

    @property
    def payload(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "chapter_key": self.chapter_key,
            "chapter_order": self.chapter_order,
            "topic": self.topic,
            "title": self.title,
            "exam_domain": self.exam_domain,
            "description": self.description,
            "content_hash": self.content_hash,
            "is_active": True,
        }


def _required_text(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} 必須是非空字串")
    return value.strip()


def _required_object(value: object, location: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{location} 必須是非空物件")
    return value


def _source_key(exam: str, chapter_key: str, topic: str, title: str) -> str:
    stable_identity = json.dumps(
        [exam, chapter_key, topic, title],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(stable_identity.encode("utf-8")).hexdigest()


def _content_hash(payload: dict[str, object]) -> str:
    stable_content = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(stable_content.encode("utf-8")).hexdigest()


def load_local_flashcards(directory: Path, exam: str) -> list[LocalFlashcard]:
    normalized_exam = exam.strip().lower()
    if normalized_exam not in EXAMS:
        raise ValueError("exam 必須是 clf 或 saa")
    if not directory.is_dir():
        raise FileNotFoundError(f"找不到 flashcards 資料夾：{directory}")

    source_file = directory / f"{normalized_exam}_flashcards.json"
    if not source_file.is_file():
        raise FileNotFoundError(f"找不到卡牌 JSON：{source_file}")

    with source_file.open(encoding="utf-8-sig") as file:
        document = json.load(file)
    chapters = _required_object(document, source_file.name)

    result: list[LocalFlashcard] = []
    seen_source_keys: set[str] = set()
    seen_chapter_orders: dict[int, str] = {}

    for raw_chapter_key, raw_topics in chapters.items():
        chapter_key = _required_text(raw_chapter_key, f"{source_file.name} chapter")
        chapter_match = CHAPTER_PATTERN.fullmatch(chapter_key)
        if not chapter_match:
            raise ValueError(
                f"{source_file.name} 的章節「{chapter_key}」必須符合 "
                "chapter數字: 名稱，例如 chapter1: What is Cloud Computing?"
            )
        chapter_order = int(chapter_match.group("order"))
        previous_chapter = seen_chapter_orders.get(chapter_order)
        if previous_chapter:
            raise ValueError(
                f"{source_file.name} 的 {previous_chapter} 與 {chapter_key} "
                f"使用相同 chapter 編號 {chapter_order}"
            )
        seen_chapter_orders[chapter_order] = chapter_key
        topics = _required_object(raw_topics, f"{source_file.name}.{chapter_key}")

        for raw_topic, raw_cards in topics.items():
            topic = _required_text(raw_topic, f"{source_file.name}.{chapter_key} topic")
            cards = _required_object(raw_cards, f"{source_file.name}.{chapter_key}.{topic}")

            for raw_title, raw_card in cards.items():
                title = _required_text(raw_title, f"{source_file.name}.{chapter_key}.{topic} title")
                card = _required_object(
                    raw_card,
                    f"{source_file.name}.{chapter_key}.{topic}.{title}",
                )
                unexpected_fields = set(card) - {"Domain", "Description"}
                if unexpected_fields:
                    raise ValueError(
                        f"{source_file.name}.{chapter_key}.{topic}.{title} "
                        f"包含不支援欄位：{sorted(unexpected_fields)}"
                    )
                exam_domain = _required_text(
                    card.get("Domain"),
                    f"{source_file.name}.{chapter_key}.{topic}.{title}.Domain",
                )
                description = _required_text(
                    card.get("Description"),
                    f"{source_file.name}.{chapter_key}.{topic}.{title}.Description",
                )
                source_key = _source_key(normalized_exam, chapter_key, topic, title)
                if source_key in seen_source_keys:
                    raise ValueError(
                        f"{source_file.name} 包含重複卡牌：{chapter_key} / {topic} / {title}"
                    )
                seen_source_keys.add(source_key)
                hash_payload = {
                    "chapter_key": chapter_key,
                    "chapter_order": chapter_order,
                    "topic": topic,
                    "title": title,
                    "exam_domain": exam_domain,
                    "description": description,
                }
                result.append(
                    LocalFlashcard(
                        source_key=source_key,
                        chapter_key=chapter_key,
                        chapter_order=chapter_order,
                        topic=topic,
                        title=title,
                        exam_domain=exam_domain,
                        description=description,
                        content_hash=_content_hash(hash_payload),
                    )
                )

    if not result:
        raise ValueError(f"{source_file.name} 沒有任何卡牌")

    result.sort(key=lambda card: (card.chapter_order, card.topic.casefold(), card.title.casefold()))
    return result
