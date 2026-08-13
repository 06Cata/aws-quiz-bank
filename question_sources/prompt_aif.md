# AWS AIF-C01 題庫內容整理規格

這份文件是給 AI 的完整工作指令。目標是同時參考雙語 AI 解析版與英文討論版 PDF，建立可供本站後續 AIF 刷題功能使用的雙語 JSON 題庫。

執行時必須實際讀取來源，不可只依一般 AWS 知識虛構題目、答案、投票比例或討論內容。

## 快速開始

```text
完整讀取 question_sources/prompt_aif.md，依照全部規則整理 AWS AIF-C01 的 Q1-Q30。
同時查閱題號對應的 with_aizh 與 with_discussion PDF。
每個 JSON 最多 30 題，輸出至 questions/aif_Q起始題號-Q結束題號.json。
不要只說明做法或只產生範例；完成後必須檢查 JSON、題號、答案與雙語欄位。
```

## 1. 檔案位置與命名

```text
aws-quiz-bank/
├── question_sources/
│   ├── prompt_aif.md
│   ├── AWS Certified AI Practitioner AIF-C01_with_aizh_part_XX.pdf
│   └── AWS Certified AI Practitioner AIF-C01_with_discussion_part_XX.pdf
└── questions/
    ├── aif_Q1-Q30.json
    ├── aif_Q31-Q60.json
    └── ...
```

- AIF-C01 題目總範圍是 Q1–Q452。
- 正式 JSON 命名固定為 `aif_Q起始題號-Q結束題號.json`。
- 每個 JSON 最多 30 題，題號必須連續、不可重複或跳號。
- `questions` 只放完成的正式 JSON；PDF 擷取文字若需暫存，應放在 `question_sources` 的暫存子資料夾。
- 兩份原始完整 PDF 保留作為封存來源；整理題目時優先使用分割後的 `part_XX`。

## 2. PDF 題號與頁面對照

兩套 PDF 使用完全相同的題號分段。每個 part 都從一題完整的新題目開始，不會從上一題的解析或留言中間開始。

### 2.1 雙語 AI 解析版

主要用於英文題幹、簡體中文翻譯、選項、官方答案及各選項解析。

| PDF | 原始 PDF 頁面 | 第一題 | 最後一題 | 題數 |
| --- | ---: | ---: | ---: | ---: |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_01.pdf` | 1–74 | Q1 | Q46 | 46 |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_02.pdf` | 75–148 | Q47 | Q92 | 46 |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_03.pdf` | 149–216 | Q93 | Q135 | 43 |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_04.pdf` | 217–290 | Q136 | Q180 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_05.pdf` | 291–368 | Q181 | Q226 | 46 |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_06.pdf` | 369–450 | Q227 | Q271 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_07.pdf` | 451–533 | Q272 | Q316 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_08.pdf` | 534–621 | Q317 | Q361 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_09.pdf` | 622–712 | Q362 | Q406 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_aizh_part_10.pdf` | 713–803 | Q407 | Q452 | 46 |

### 2.2 英文討論版

主要用於社群投票、熱門留言、答案爭議與考點補充。

| PDF | 原始 PDF 頁面 | 第一題 | 最後一題 | 題數 |
| --- | ---: | ---: | ---: | ---: |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_01.pdf` | 1–92 | Q1 | Q46 | 46 |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_02.pdf` | 93–164 | Q47 | Q92 | 46 |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_03.pdf` | 165–227 | Q93 | Q135 | 43 |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_04.pdf` | 228–282 | Q136 | Q180 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_05.pdf` | 283–334 | Q181 | Q226 | 46 |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_06.pdf` | 335–382 | Q227 | Q271 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_07.pdf` | 383–432 | Q272 | Q316 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_08.pdf` | 433–480 | Q317 | Q361 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_09.pdf` | 481–526 | Q362 | Q406 | 45 |
| `AWS Certified AI Practitioner AIF-C01_with_discussion_part_10.pdf` | 527–576 | Q407 | Q452 | 46 |

若指定範圍跨越 part 邊界，必須讀取兩個相鄰 part。例如 Q40–Q55 需要同時查看 `part_01` 的 Q40–Q46 與 `part_02` 的 Q47–Q55。

## 3. 題目整理流程

1. 先掃描所有 `questions/aif_Q*-Q*.json` 內的 `question_no`，確認現有題號連續。
2. 指定範圍的第一題必須等於現有最後一題加 1；若尚無 AIF 題庫則從 Q1 開始。
3. 在兩套 PDF 中搜尋 `Question #題號`。
4. 擷取從該題標題至下一題標題前的完整內容，跨頁內容必須合併。
5. 以 `with_aizh` 的答案為起點，再依 AWS 技術原理及 `with_discussion` 的投票與留言交叉檢查。
6. 清除 `Most Voted`、頁首頁尾、下載日期、微信、淘寶、閒魚、帳號、網址與其他廣告雜訊。
7. 修正 OCR 亂碼，並補齊自然、完整的簡體中文與英文內容。
8. 若官方答案與社群意見衝突，在 `discussion` 說明爭議與最終技術判斷，不可只採最高票。

## 4. AIF-C01 考試領域

`domain` 必須完全使用以下五個值之一：

- `領域 1：AI 和 ML 基礎 (Fundamentals of AI and ML)` — 20%
- `領域 2：生成式 AI 基礎 (Fundamentals of GenAI)` — 24%
- `領域 3：基礎模型的應用 (Applications of Foundation Models)` — 28%
- `領域 4：負責任 AI 指南 (Guidelines for Responsible AI)` — 14%
- `領域 5：AI 解決方案的安全、合規與治理 (Security, Compliance, and Governance for AI Solutions)` — 14%

判斷提示：

- AI／ML 概念、訓練與推論、監督式／非監督式學習、評估指標 → 領域 1
- 生成式 AI 概念、tokens、embeddings、transformers、基礎模型生命週期 → 領域 2
- Prompt engineering、RAG、fine-tuning、agents、模型選擇與應用 → 領域 3
- 公平性、偏見、透明度、可解釋性、可信任與負責任 AI → 領域 4
- IAM、加密、資料隱私、合規、治理、稽核與安全控制 → 領域 5

同時涉及多個領域時，依題目的主要決策與考點分類，不要只看服務名稱。

## 5. JSON Schema

最外層固定為：

```json
{
  "exam": "AWS AIF-C01",
  "questions": []
}
```

每題固定使用：

```json
{
  "question_no": 1,
  "domain": "領域 4：負責任 AI 指南 (Guidelines for Responsible AI)",
  "question_text": {
    "zh": "完整簡體中文題幹",
    "en": "Complete English question"
  },
  "options": {
    "A": {"zh": "簡體中文選項 A", "en": "English option A"},
    "B": {"zh": "簡體中文選項 B", "en": "English option B"},
    "C": {"zh": "簡體中文選項 C", "en": "English option C"},
    "D": {"zh": "簡體中文選項 D", "en": "English option D"}
  },
  "option_explanations": {
    "A": {"zh": "錯誤。完整技術原因。", "en": "Incorrect. Complete technical reason."},
    "B": {"zh": "正確。完整技術原因。", "en": "Correct. Complete technical reason."},
    "C": {"zh": "錯誤。完整技術原因。", "en": "Incorrect. Complete technical reason."},
    "D": {"zh": "錯誤。完整技術原因。", "en": "Incorrect. Complete technical reason."}
  },
  "selection_type": "單選",
  "correct_answers": ["B"],
  "answer_text": {
    "zh": "B. 完整簡體中文選項",
    "en": "B. Complete English option"
  },
  "discussion": {
    "zh": "社群投票、爭議與考點摘要。",
    "en": "Community vote, controversy, and key concept summary."
  }
}
```

## 6. JSON 強制規則

- UTF-8 合法 JSON，不使用 Markdown code fence 包住正式輸出。
- 所有字串都是單行，不可包含實際換行、空字串、`null`、`TODO` 或省略號佔位。
- 題幹只放情境與問題，不混入選項、答案、投票或留言。
- 選項依原題保留 A–F；`options` 與 `option_explanations` 的代號必須完全相同。
- 每個選項都要有獨立的中英文解析，不可只重述選項。
- 正確選項的中文解析以「正確。」開頭，英文以 `Correct.` 開頭。
- 錯誤選項的中文解析以「錯誤。」開頭，英文以 `Incorrect.` 開頭。
- 一個答案時 `selection_type` 是 `單選`；兩個以上答案時是 `複選`。
- `correct_answers` 只放存在於選項中的代號，依字母順序排列。
- `answer_text` 必須包含答案代號與完整選項文字，並與 `correct_answers` 一致。
- `discussion` 應摘要真實投票與留言；來源沒有百分比時，明確說明未提供，不可捏造。

## 7. 完成檢查

- [ ] 檔名、題數與內部題號範圍一致。
- [ ] 題號連續，沒有重複或缺漏。
- [ ] JSON 可解析，所有必要欄位存在。
- [ ] 題幹、選項、解析、答案及討論都有 `zh` 與 `en`。
- [ ] 正確答案與每個選項解析開頭一致。
- [ ] 簡體中文自然完整，沒有 OCR 亂碼。
- [ ] 投票內容忠於來源，沒有廣告或帳號資訊。

完成 JSON 後，請回到 `AWS_QUIZ_BUILD_GUIDE.md` 的「AIF 步驟 8–9」進行驗證與同步。本文件只維護產題內容規格，不重複放置建表、同步或部署指令。
