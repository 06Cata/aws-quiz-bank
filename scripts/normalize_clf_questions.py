#!/usr/bin/env python3
"""Normalize CLF explanations and expand short or generic option analysis."""

from __future__ import annotations

import json
import re
from pathlib import Path

from normalize_saa_questions import matched_purposes, requirement_summary


ROOT = Path(__file__).resolve().parents[1]
QUESTION_DIR = ROOT / "questions"

GENERIC_REASONS = {
    "因此不符合题目要求。",
    "因此不符合题目要求",
    "此选项不符合问题所需的 AWS 功能或责任范围。",
    "此选项不符合问题所需的 AWS 功能或责任范围",
}

SPECIAL_OVERRIDES: dict[tuple[int, str], str] = {
    (250, "B"): "Dedicated Instance 在單一租戶硬體上執行 EC2，主要解決合規或隔離需求，價格通常較高；它不會利用可中斷的 AWS 閒置容量來降低無狀態工作的成本。",
    (250, "D"): "On-Demand Instance 無須長期承諾並按使用量付費，適合不可預測或短期工作；但它沒有 Spot 的閒置容量折扣，不是本題最低成本方案。",
    (359, "A"): "AWS 隨用隨付模式把購買資料中心設備的前期資本支出轉成依實際用量產生的變動支出，因此能避免閒置容量並降低總持有成本。",
    (385, "B"): "IAM Identity Center 集中管理員工對多個 AWS 帳戶與應用程式的登入及權限，但不分析 S3 bucket policy、IAM role 等資源是否允許外部帳戶存取；此工作應使用 IAM Access Analyzer。",
    (447, "C"): "Root user access key 提供程式化的完整帳戶權限，一旦外洩風險極高；安全最佳實務是不要建立或使用 root access key，並為特權使用者啟用 MFA。",
}


def strip_prefix(text: str, status: str) -> str:
    text = text.strip()
    if text.startswith(status):
        text = text[len(status):].lstrip()
    text = re.sub(r"^(?:技術原因|技术原因|原因是|原因|分析|理由)\s*[：，,:]?\s*", "", text)
    return text.strip()


def expand_reason(question: dict, key: str, reason: str, is_correct: bool) -> str:
    option = question["options"][key]["zh"].strip()
    purposes = matched_purposes(option)
    useful_existing = reason not in GENERIC_REASONS and len(reason) >= 12
    parts: list[str] = []
    if purposes and not any(purpose.split("，", 1)[0] in reason for purpose in purposes):
        parts.append("；".join(purposes) + "。")
    if useful_existing:
        parts.append(reason)
    elif not purposes:
        parts.append(f"此選項描述的是「{option.rstrip('。')}」這項做法。")

    requirement = requirement_summary(question["question_text"]["zh"])
    if is_correct:
        parts.append(f"這項能力正好用來處理「{requirement}」，所以是本題正確選項。")
    else:
        correct = "；".join(
            question["options"][answer]["zh"].strip()
            for answer in question["correct_answers"]
        )[:180]
        parts.append(
            f"它無法取代本題需要的「{correct}」能力，因此不適合「{requirement}」的情境。"
        )
    return "".join(parts)


def main() -> None:
    changed_files = 0
    changed_options = 0
    expanded_options = 0
    for path in sorted(QUESTION_DIR.glob("clf_Q*-Q*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        file_changed = False
        for question in document["questions"]:
            correct_answers = set(question["correct_answers"])
            for key, explanation in question["option_explanations"].items():
                is_correct = key in correct_answers
                status = "正確。" if is_correct else "錯誤。"
                original = explanation["zh"]
                reason = strip_prefix(original, status)
                override = SPECIAL_OVERRIDES.get((question["question_no"], key))
                if override:
                    reason = override
                elif reason in GENERIC_REASONS or len(reason) < 25:
                    reason = expand_reason(question, key, reason, is_correct)
                    expanded_options += 1
                updated = f"{status}原因是，{reason}"
                if updated != original:
                    explanation["zh"] = updated
                    changed_options += 1
                    file_changed = True
        if file_changed:
            path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            changed_files += 1
    print(
        f"normalized CLF explanations: files={changed_files}, "
        f"options={changed_options}, expanded={expanded_options}"
    )


if __name__ == "__main__":
    main()
