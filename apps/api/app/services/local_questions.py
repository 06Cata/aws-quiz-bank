import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


QUESTION_FILE_PATTERN = re.compile(r"^Q(?P<start>\d+)-Q(?P<end>\d+)\.json$", re.IGNORECASE)
OPTION_KEYS = set("ABCDEF")
EXAM_NAMES = {
    "clf": {"AWS CLF-C02", "AWS Cloud Practitioner"},
    "saa": {"AWS SAA-C03", "AWS Solutions Architect Associate"},
}


@dataclass(frozen=True)
class LocalQuestion:
    question_no: int
    source_file: Path
    source_index: int
    payload: dict[str, Any]


def _required_text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} 必須是非空字串")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{location} 不可包含換行")
    return value.strip()


def _bilingual(value: Any, location: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{location} 必須是包含 zh、en 的物件")
    return {
        "zh": _required_text(value.get("zh"), f"{location}.zh"),
        "en": _required_text(value.get("en"), f"{location}.en"),
    }


def _option_map(value: Any, location: str) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{location} 必須是非空物件")

    result: dict[str, dict[str, str]] = {}
    for raw_key, option in value.items():
        key = str(raw_key).strip().upper()
        if key not in OPTION_KEYS:
            raise ValueError(f"{location} 包含不支援的選項代號：{raw_key}")
        result[key] = _bilingual(option, f"{location}.{key}")
    return dict(sorted(result.items()))


def _content_hash(payload: dict[str, Any]) -> str:
    source = {
        "question_text": payload["question_text"],
        "options": payload["options"],
        "correct_options": payload["correct_options"],
    }
    stable = json.dumps(source, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _normalize_question(
    question: Any,
    source_file: Path,
    source_index: int,
    exam: str,
) -> LocalQuestion:
    location = f"{source_file.name} questions[{source_index}]"
    if not isinstance(question, dict):
        raise ValueError(f"{location} 必須是物件")

    question_no = question.get("question_no", question.get("no"))
    if not isinstance(question_no, int) or isinstance(question_no, bool) or question_no < 1:
        raise ValueError(f"{location}.question_no 必須是正整數")

    options = _option_map(question.get("options"), f"{location}.options")
    explanations = _option_map(
        question.get("option_explanations"),
        f"{location}.option_explanations",
    )
    if options.keys() != explanations.keys():
        raise ValueError(f"{location} 的 options 與 option_explanations 代號不一致")

    correct_options = question.get("correct_answers")
    if not isinstance(correct_options, list) or not correct_options:
        raise ValueError(f"{location}.correct_answers 必須是非空陣列")
    correct_options = [str(item).strip().upper() for item in correct_options]
    if len(correct_options) != len(set(correct_options)):
        raise ValueError(f"{location}.correct_answers 不可重複")
    if not set(correct_options).issubset(options):
        raise ValueError(f"{location}.correct_answers 包含不存在的選項")

    for key, explanation in explanations.items():
        is_correct = key in correct_options
        expected_zh = "正確。" if is_correct else "錯誤。"
        expected_en = "Correct." if is_correct else "Incorrect."
        if not explanation["zh"].startswith(expected_zh):
            raise ValueError(
                f"{location}.option_explanations.{key}.zh 必須以「{expected_zh}」開頭"
            )
        if not explanation["en"].startswith(expected_en):
            raise ValueError(
                f"{location}.option_explanations.{key}.en 必須以 {expected_en} 開頭"
            )
        if explanation["zh"][len(expected_zh):].lstrip().startswith(options[key]["zh"]):
            raise ValueError(
                f"{location}.option_explanations.{key}.zh 不可先重複選項原文"
            )
        if explanation["en"][len(expected_en):].lstrip().startswith(options[key]["en"]):
            raise ValueError(
                f"{location}.option_explanations.{key}.en 不可先重複選項原文"
            )

    selection_type = _required_text(question.get("selection_type"), f"{location}.selection_type")
    expected_type = "單選" if len(correct_options) == 1 else "複選"
    if selection_type != expected_type:
        raise ValueError(
            f"{location}.selection_type 應為 {expected_type}，但收到 {selection_type}"
        )

    payload: dict[str, Any] = {
        "source": "local_json",
        # 相容目前資料表的既有非空欄位；值代表本機 JSON，而非 Google Sheet。
        "source_sheet_id": "local-json",
        "source_sheet_name": source_file.name,
        "source_row_number": source_index + 1,
        "question_no": question_no,
        "exam_domain": _required_text(question.get("domain"), f"{location}.domain"),
        "question_text": _bilingual(question.get("question_text"), f"{location}.question_text"),
        "options": options,
        "option_explanations": explanations,
        "correct_options": correct_options,
        "answer_text": _bilingual(question.get("answer_text"), f"{location}.answer_text"),
        "choice_type": "single" if selection_type == "單選" else "multiple",
        "discussion": _bilingual(question.get("discussion"), f"{location}.discussion"),
        "is_active": True,
    }
    if exam == "clf":
        payload["certification"] = "AWS Cloud Practitioner"
    payload["content_hash"] = _content_hash(payload)

    return LocalQuestion(
        question_no=question_no,
        source_file=source_file,
        source_index=source_index,
        payload=payload,
    )


def load_local_questions(directory: Path, exam: str) -> list[LocalQuestion]:
    normalized_exam = exam.strip().lower()
    if normalized_exam not in EXAM_NAMES:
        raise ValueError("exam 必須是 clf 或 saa")
    if not directory.is_dir():
        raise FileNotFoundError(f"找不到 questions 資料夾：{directory}")

    files: list[tuple[int, int, Path]] = []
    for path in directory.glob("*.json"):
        match = QUESTION_FILE_PATTERN.fullmatch(path.name)
        if not match:
            continue
        start, end = int(match.group("start")), int(match.group("end"))
        if start > end:
            raise ValueError(f"{path.name} 的起始題號不可大於結束題號")
        if end - start + 1 > 15:
            raise ValueError(f"{path.name} 超過每個檔案最多 15 題的限制")
        files.append((start, end, path))
    files.sort(key=lambda item: (item[0], item[1], item[2].name.lower()))
    if not files:
        raise ValueError(f"{directory} 中沒有符合 Qx-Qy.json 格式的題庫檔案")

    result: list[LocalQuestion] = []
    seen: dict[int, Path] = {}
    for file_start, file_end, path in files:
        with path.open(encoding="utf-8-sig") as file:
            document = json.load(file)
        if not isinstance(document, dict) or not isinstance(document.get("questions"), list):
            raise ValueError(f"{path.name} 必須是包含 questions 陣列的 JSON 物件")

        document_exam = _required_text(document.get("exam"), f"{path.name}.exam")
        if document_exam not in EXAM_NAMES[normalized_exam]:
            continue

        file_questions = [
            _normalize_question(question, path, index, normalized_exam)
            for index, question in enumerate(document["questions"])
        ]
        actual_numbers = [item.question_no for item in file_questions]
        expected_numbers = list(range(file_start, file_end + 1))
        if actual_numbers != expected_numbers:
            raise ValueError(
                f"{path.name} 題號必須完整且依序為 Q{file_start}-Q{file_end}，"
                f"實際為 {actual_numbers}"
            )
        for item in file_questions:
            previous = seen.get(item.question_no)
            if previous:
                raise ValueError(
                    f"Q{item.question_no} 同時出現在 {previous.name} 與 {path.name}"
                )
            seen[item.question_no] = path
            result.append(item)

    if not result:
        raise ValueError(f"沒有符合 {normalized_exam} 的本機 JSON 題目")
    result.sort(key=lambda item: item.question_no)
    numbers = [item.question_no for item in result]
    expected = list(range(1, numbers[-1] + 1))
    if numbers != expected:
        missing = sorted(set(expected) - set(numbers))
        raise ValueError(f"本機題庫必須從 Q1 開始且不可跳號，目前缺少：{missing}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="驗證本機 Qx-Qy.json 題庫")
    parser.add_argument("directory", type=Path, help="questions 資料夾")
    parser.add_argument("--exam", choices=sorted(EXAM_NAMES), default="saa")
    args = parser.parse_args()
    questions = load_local_questions(args.directory.resolve(), args.exam)
    print(
        f"Local JSON validation completed for {args.exam}: "
        f"questions={len(questions)}, latest=Q{questions[-1].question_no}"
    )


if __name__ == "__main__":
    main()
