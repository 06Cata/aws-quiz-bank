"""Build bilingual AIF-C01 question JSON from the local source PDFs."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "question_sources"
OUTPUT_DIR = ROOT / "questions"
QUESTION_RE = re.compile(r"(?:Topic\s+\d+\s*)?Question\s*#(\d+)", re.IGNORECASE)
OPTION_RE = re.compile(r"(?m)^[ \t]*([A-F])\.\s*")
CHINESE_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
NOISE_RE = re.compile(
    r"IT认证轻松过|下载时间|使用指南|扫码关注|淘宝|闲鱼|微信|Examtopics|"
    r"Community vote distribution|社区投票分布",
    re.IGNORECASE,
)

DOMAINS = {
    1: "領域 1：AI 和 ML 基礎 (Fundamentals of AI and ML)",
    2: "領域 2：生成式 AI 基礎 (Fundamentals of GenAI)",
    3: "領域 3：基礎模型的應用 (Applications of Foundation Models)",
    4: "領域 4：負責任 AI 指南 (Guidelines for Responsible AI)",
    5: "領域 5：AI 解決方案的安全、合規與治理 (Security, Compliance, and Governance for AI Solutions)",
}

DOMAIN_RULES = (
    (5, (" iam ", "identity", "permission", "access control", "encrypt", "kms", "privacy", "pii", "compliance", "governance", "audit", "security", "guardrail", "macie")),
    (4, ("bias", "fairness", "responsible", "transparent", "transparency", "explain", "interpret", "toxicity", "harmful", "human review", "moderation", "inappropriate", "unwanted")),
    (3, ("prompt", "rag", "retrieval", "fine-tun", "fine tun", "agent", "knowledge base", "bedrock", "amazon q", "model selection", "temperature", "top_p", "context window")),
    (2, ("generative", "large language model", "llm", "foundation model", "token", "embedding", "transformer", "diffusion", "pretrain", "pre-train")),
)

ZH_OPTION_FALLBACKS = {
    "Decision trees": "决策树",
    "Linear regression": "线性回归",
    "Logistic regression": "逻辑回归",
    "Neural networks": "神经网络",
    "R-squared score": "R² 决定系数",
    "Accuracy": "准确率",
    "Root mean squared error (RMSE)": "均方根误差（RMSE）",
    "Learning rate": "学习率",
    "Temperature": "温度",
    "Context window": "上下文窗口",
    "Batch size": "批次大小",
    "Model size": "模型大小",
    "Object detection": "目标检测",
    "Anomaly detection": "异常检测",
    "Named entity recognition": "命名实体识别",
    "Inpainting": "图像修复",
    "Generative pre-trained transformers (GPT)": "生成式预训练 Transformer（GPT）",
    "Residual neural network": "残差神经网络",
    "Support vector machine": "支持向量机",
    "WaveNet": "WaveNet 音频生成模型",
    "Training": "训练",
    "Inference": "推理",
    "Model deployment": "模型部署",
    "Bias correction": "偏差修正",
    "Toxicity": "毒性",
    "Hallucinations": "幻觉",
    "Plagiarism": "抄袭",
    "Privacy": "隐私",
    "Generative adversarial network (GAN)": "生成对抗网络（GAN）",
    "XGBoost": "XGBoost 梯度提升算法",
    "Confusion matrix": "混淆矩阵",
    "Correlation matrix": "相关矩阵",
    "R2 score": "R² 决定系数",
    "Mean squared error (MSE)": "均方误差（MSE）",
    "Batch transform": "批量转换",
    "Real-time inference": "实时推理",
    "Serverless inference": "无服务器推理",
    "Asynchronous inference": "异步推理",
    "Embeddings": "嵌入（Embeddings）",
    "Tokens": "词元（Tokens）",
    "Models": "模型",
    "Binaries": "二进制数据",
    "Bilingual Evaluation Understudy (BLEU)": "双语评估替补指标（BLEU）",
    "Recall-Oriented Understudy for Gisting Evaluation (ROUGE)": "面向摘要的召回率评估指标（ROUGE）",
    "F1 score": "F1 分数",
    "Temperature value": "温度值",
    "Adversarial prompting": "对抗式提示",
    "Zero-shot prompting": "零样本提示",
    "Least-to-most prompting": "由简至繁提示",
    "Chain-of-thought prompting": "思维链提示",
    "Precision": "精确率",
    "Time to first token": "首个 token 生成时间",
    "Word error rate": "词错误率",
    "Explainability": "可解释性",
    "Experiment and refine the prompt until the FM produces the desired responses.": "持续试验并优化提示，直到基础模型产生所需响应。",
    "Amazon EC2 Trn series": "Amazon EC2 Trn 系列",
    "Enable invocation logging in Amazon Bedrock.": "在 Amazon Bedrock 中启用模型调用日志记录。",
    "Create one Amazon Bedrock role that has full Amazon S3 access. Create IAM roles for each team that have access to only each team's customer folders.": "建立一个拥有完整 Amazon S3 访问权限的 Amazon Bedrock 角色，并为各团队建立只能访问本团队客户文件夹的 IAM 角色。",
    "Decrease the number of tokens in the prompt.": "减少提示中的 token 数量。",
}


def pdf_text(kind: str, parts: tuple[int, ...]) -> str:
    chunks: list[str] = []
    for part in parts:
        path = SOURCE_DIR / f"AWS Certified AI Practitioner AIF-C01_with_{kind}_part_{part:02d}.pdf"
        reader = PdfReader(path)
        if kind == "aizh":
            chunks.extend(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)
        else:
            chunks.extend(page.extract_text() or "" for page in reader.pages)
    return "\n".join(chunks)


def question_blocks(text: str) -> dict[int, str]:
    matches = list(QUESTION_RE.finditer(text))
    result: dict[int, str] = {}
    for index, match in enumerate(matches):
        number = int(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[number] = text[match.end():end]
    return result


def clean_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\bMost Voted\b", "", value, flags=re.IGNORECASE)
    kept: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or NOISE_RE.search(line):
            continue
        if re.fullmatch(r"[()\d% ,]+", line):
            continue
        kept.append(line)
    value = " ".join(kept)
    value = re.sub(r"\s+", " ", value).strip()
    for _ in range(3):
        value = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", value)
    value = re.sub(r"\s+([,.;:?!，。；：？！])", r"\1", value)
    return value.strip()


def source_header(block: str, marker: str) -> str:
    positions = [pos for token in (marker, "Comments", "Correct Answer:") if (pos := block.find(token)) >= 0]
    return block[: min(positions)] if positions else block


def parse_header(block: str, marker: str) -> tuple[str, dict[str, str]]:
    header = source_header(block, marker)
    matches = list(OPTION_RE.finditer(header))
    if not matches:
        raise ValueError("No options found")
    question = clean_text(header[: matches[0].start()])
    options: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(header)
        options[match.group(1)] = clean_text(header[match.end():end])
    return question, options


def split_bilingual(value: str) -> tuple[str, str]:
    match = CHINESE_RE.search(value)
    if not match:
        cleaned = clean_text(value)
        return cleaned, cleaned
    en = clean_text(value[: match.start()])
    zh = clean_text(value[match.start():])
    return en or zh, zh or en


def clean_zh_option(en: str, raw_zh: str) -> str:
    value = clean_text(raw_zh)
    marker = re.search(
        r"\s*[)）]?\s*(?:问题点|正确点|正确性分析|是否支持|可解释性|错误[。:]|正确[。:]|"
        r"结论[：:]|原因[：:]|题目解析|官方答案|答案比较|与官方答案|[3456]\.\s*)",
        value,
    )
    if marker:
        value = value[: marker.start()].strip()
    value = value.rstrip(" )）")
    if not CHINESE_RE.search(value) or len(value) < 2:
        return ZH_OPTION_FALLBACKS.get(en, en)
    return value


def source_zh_explanations(block: str, options: dict[str, str], answers: list[str]) -> dict[str, str]:
    matches = list(OPTION_RE.finditer(block))
    candidates: dict[str, list[tuple[int, str]]] = {key: [] for key in options}
    for index, match in enumerate(matches):
        key = match.group(1)
        if key not in candidates:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        segment = clean_text(block[match.end():end])
        option_text = clean_text(options[key])
        if segment.lower().startswith(option_text.lower()):
            segment = segment[len(option_text):].strip()
        marker = re.search(r"(?:正确|错误|问题点|正确点|是否支持|可解释性|原因|结论)[：:]?", segment)
        if not marker:
            continue
        if re.search(r"Correct Answer|题目解析|题目分析|官方答案|我的答案|答案比较|与官方答案", segment[: marker.start()]):
            continue
        reason = segment[marker.start():]
        reason = re.split(
            r"(?:\b[3456]\.\s*(?:我的答案|官方答案|与官方答案|答案比较|比较与思考)|"
            r"Correct Answer|Community vote|题目解析|题目分析|我的答案|官方答案|与官方答案|答案比较)",
            reason,
        )[0]
        score = len(reason) + 200 * len(re.findall(r"正确|错误|原因|结论", reason))
        candidates[key].append((score, reason.strip()))

    result: dict[str, str] = {}
    for key, rows in candidates.items():
        if not rows:
            continue
        reason = max(rows, key=lambda item: item[0])[1]
        reason = re.sub(r"^(?:正确|错误|问题点|正确点|是否支持|可解释性|原因|结论)[：:]?\s*", "", reason)
        reason = reason.strip(" 。；;:")
        if reason:
            prefix = "正確。" if key in answers else "錯誤。"
            result[key] = f"{prefix}原因是，{reason[:900]}"
    return result


def correct_answers(block: str) -> list[str]:
    matches = re.findall(r"Correct\s*Answer\s*:\s*([A-F](?:\s*[,/&+]\s*[A-F]|[A-F])*)", block, re.IGNORECASE)
    if not matches:
        raise ValueError("Correct answer not found")
    letters = sorted(set(re.findall(r"[A-F]", matches[-1].upper())))
    return letters


def vote_distribution(block: str) -> str | None:
    anchor = block.rfind("Community vote distribution")
    if anchor < 0:
        return None
    tail = unicodedata.normalize("NFKC", block[anchor : anchor + 500])
    votes = re.findall(r"\b([A-F]|Other)\s*\((\d+)%\)", tail, re.IGNORECASE)
    if not votes:
        return None
    return ", ".join(f"{label.upper() if label.lower() != 'other' else 'Other'} {percent}%" for label, percent in votes)


def domain_for(question: str, options: dict[str, str]) -> str:
    haystack = f" {question.lower()} "
    for domain, keywords in DOMAIN_RULES:
        if any(keyword in haystack for keyword in keywords):
            return DOMAINS[domain]
    return DOMAINS[1]


def compact_requirement(question: str) -> str:
    sentences = re.split(r"(?<=[?.!])\s+", question)
    return (sentences[-1] if sentences else question)[:360]


def build_question(number: int, aizh: str, discussion: str) -> dict:
    en_question, en_options = parse_header(discussion, "Comments")
    bilingual_question, bilingual_options = parse_header(aizh, "题目解析")
    _, zh_question = split_bilingual(bilingual_question)
    zh_options: dict[str, str] = {}
    for key, value in bilingual_options.items():
        _, zh = split_bilingual(value)
        zh_options[key] = clean_zh_option(en_options.get(key, ""), zh)

    if set(en_options) != set(zh_options):
        raise ValueError(f"Q{number}: English and bilingual option keys differ")

    answers = correct_answers(aizh)
    zh_source_reasons = source_zh_explanations(aizh, en_options, answers)
    requirement = compact_requirement(en_question)
    correct_en = "; ".join(f"{key}. {en_options[key]}" for key in answers)
    correct_zh = "；".join(f"{key}. {zh_options[key]}" for key in answers)
    explanations: dict[str, dict[str, str]] = {}
    for key in en_options:
        if key in answers:
            explanations[key] = {
                "zh": zh_source_reasons.get(key, f"正確。此選項直接滿足題目要求，並且是來源解析確認的答案；本題的核心判斷是：{zh_question[-220:]}"),
                "en": f"Correct. Choosing this option directly addresses the source-confirmed requirement: {requirement}",
            }
        else:
            explanations[key] = {
                "zh": zh_source_reasons.get(key, f"錯誤。此選項不能完整滿足題目的主要要求；相較之下，來源確認的適當答案是 {correct_zh}。"),
                "en": f"Incorrect. This option addresses a different task or misses a key constraint in: {requirement} The source-supported choice is {correct_en}.",
            }

    vote = vote_distribution(aizh) or vote_distribution(discussion)
    if vote:
        discussion_zh = f"來源社群投票分布為 {vote}。討論重點是比較各選項是否真正滿足題目主要需求；最終答案依來源解析與技術判斷採用 {', '.join(answers)}。"
        discussion_en = f"The source community vote distribution is {vote}. The discussion focuses on whether each option satisfies the primary requirement; the final answer follows the source analysis and technical reasoning: {', '.join(answers)}."
    else:
        discussion_zh = f"來源未提供可可靠擷取的投票百分比。最終答案依來源解析與技術判斷採用 {', '.join(answers)}。"
        discussion_en = f"The source does not provide a reliably extractable vote percentage. The final answer follows the source analysis and technical reasoning: {', '.join(answers)}."

    return {
        "question_no": number,
        "domain": domain_for(en_question, en_options),
        "question_text": {"zh": zh_question, "en": en_question},
        "options": {key: {"zh": zh_options[key], "en": en_options[key]} for key in en_options},
        "option_explanations": explanations,
        "selection_type": "單選" if len(answers) == 1 else "複選",
        "correct_answers": answers,
        "answer_text": {
            "zh": correct_zh,
            "en": correct_en,
        },
        "discussion": {"zh": discussion_zh, "en": discussion_en},
    }


def write_batches(questions: list[dict], batch_size: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for offset in range(0, len(questions), batch_size):
        batch = questions[offset : offset + batch_size]
        start = batch[0]["question_no"]
        end = batch[-1]["question_no"]
        path = OUTPUT_DIR / f"aif_Q{start}-Q{end}.json"
        path.write_text(
            json.dumps({"exam": "AWS AIF-C01", "questions": batch}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"{path.name}: {len(batch)} questions")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=30)
    args = parser.parse_args()
    if args.start < 1 or args.end < args.start or not 1 <= args.batch_size <= 30:
        raise ValueError("Use a valid range and a batch size from 1 to 30")

    last_part = 1 if args.end <= 46 else 2 if args.end <= 92 else 3
    parts = tuple(range(1, last_part + 1))
    aizh_blocks = question_blocks(pdf_text("aizh", parts))
    discussion_blocks = question_blocks(pdf_text("discussion", parts))
    questions: list[dict] = []
    for number in range(args.start, args.end + 1):
        if number not in aizh_blocks or number not in discussion_blocks:
            raise ValueError(f"Q{number}: source block missing")
        questions.append(build_question(number, aizh_blocks[number], discussion_blocks[number]))
    write_batches(questions, args.batch_size)


if __name__ == "__main__":
    main()
