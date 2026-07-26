#!/usr/bin/env python3
"""Format CLF/SAA descriptions into short, readable paragraphs."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMS = ("clf", "saa")
MAX_PARAGRAPH_LENGTH = 180
SECTION_LABELS = (
    "補充與常見考法：",
    "常見情境與考法：",
    "常見考法：",
)
SECTION_LABEL_PATTERN = re.compile(
    "|".join(re.escape(label) for label in SECTION_LABELS)
)


def _split_long_sentence(sentence: str) -> list[str]:
    if len(sentence) <= MAX_PARAGRAPH_LENGTH:
        return [sentence]
    clauses = [part for part in re.split(r"(?<=[，；])", sentence) if part]
    if len(clauses) == 1:
        return [sentence]
    chunks: list[str] = []
    current = ""
    for clause in clauses:
        if current and len(current) + len(clause) > MAX_PARAGRAPH_LENGTH:
            chunks.append(current.strip())
            current = clause
        else:
            current += clause
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _split_paragraph(paragraph: str) -> list[str]:
    paragraph = paragraph.strip()
    if not paragraph:
        return []
    sentences = [
        chunk.strip()
        for chunk in re.split(r"(?<=[。！？；])", paragraph)
        if chunk.strip()
    ]
    if not sentences:
        return [paragraph]
    units = [part for sentence in sentences for part in _split_long_sentence(sentence)]
    result: list[str] = []
    current = ""
    for unit in units:
        separator = "" if not current else ""
        candidate = current + separator + unit
        if current and len(candidate) > MAX_PARAGRAPH_LENGTH:
            result.append(current.strip())
            current = unit
        else:
            current = candidate
    if current.strip():
        result.append(current.strip())
    return result


def format_description(description: str) -> str:
    normalized = description.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = SECTION_LABEL_PATTERN.sub(
        lambda match: match.group(0)
        if match.start() == 0 or normalized[max(0, match.start() - 2):match.start()] == "\n\n"
        else f"\n\n{match.group(0)}",
        normalized,
    )
    raw_paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    paragraphs = [piece for paragraph in raw_paragraphs for piece in _split_paragraph(paragraph)]
    return "\n\n".join(paragraphs)


def format_exam(exam: str) -> tuple[int, int]:
    source = ROOT / "flashcards_sources" / f"{exam}_flashcards.json"
    data = json.loads(source.read_text())
    changed = 0
    total = 0
    for topics in data.values():
        for cards in topics.values():
            for card in cards.values():
                total += 1
                formatted = format_description(card["Description"])
                if formatted != card["Description"]:
                    card["Description"] = formatted
                    changed += 1
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    for directory in ("flashcards_sources", "flashcards"):
        (ROOT / directory / f"{exam}_flashcards.json").write_text(rendered)
    return total, changed


def main() -> None:
    for exam in EXAMS:
        total, changed = format_exam(exam)
        print(f"{exam.upper()}: cards={total}, descriptions_changed={changed}")


if __name__ == "__main__":
    main()
