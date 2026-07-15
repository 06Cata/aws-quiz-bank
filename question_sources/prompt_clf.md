# AWS CLF-C02 題庫整理操作手冊

這份文件是給 AI 的完整工作指令。目標是從兩種 PDF 來源整理出可直接被專案驗證及同步的雙語 JSON 題庫。

執行時必須從步驟 0 開始，依序完成所有步驟。不要詢問是否繼續，也不要只提供範例；必須實際建立檔案並完成驗證。

## 快速開始：指定題號範圍

把下面指令中的 `Q11-Q100` 換成這次要整理的完整範圍，然後直接交給 AI：

```text
完整讀取 question_sources/prompt_clf.md，依照全部規則整理 AWS CLF-C02 的 Q11-Q100。
Q11-Q100 是本次要完成的總範圍；每個 JSON 最多 30 題，請自動連續拆檔，不可把 90 題寫進同一個檔案。
開始前先掃描 questions/clf_Q*-Q*.json 內的 question_no，確認指定的第一題等於現有最後一題加 1，且既有題號沒有重複或缺漏；不符合時停止並回報。
同時查閱題號對應的 with_aizh 與 with_discussion PDF，實際建立所有 JSON 檔案，最後執行 npm run validate:questions:clf，修正到驗證通過。所有檔案的 exam 必須是 AWS CLF-C02，後續只同步至 Supabase questions table。
不要只說明做法、不要只產生範例，也不要每完成一批就詢問是否繼續。
```

例如指定 `Q11-Q100` 時，必須自動輸出：

```text
questions/clf_Q11-Q40.json
questions/clf_Q41-Q70.json
questions/clf_Q71-Q100.json
```

指定範圍規則：

- 格式固定為 `clf_Q起始題號-Q結束題號.json`，例如 `clf_Q101-Q130.json`。
- 起始題號必須接在現有正式題庫最後一題之後，不能覆蓋或跳過既有題目。
- 結束題號可以不是 30 的倍數；最後一檔只放剩餘題目。
- CLF-C02 可指定的最高題號是 Q719。

---

## 0. 先了解資料夾用途

```text
aws-quiz-bank/
├── question_sources/
│   ├── prompt_clf.md
│   ├── AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_XX.pdf
│   ├── AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_XX.pdf
│   └── clf_questions_XX-XX_raw/        # 暫存的 PDF 提取文字，可選
└── questions/
    ├── clf_Q1-Q30.json
    ├── clf_Q31-Q60.json
    ├── clf_Q61-Q90.json
    └── ...                         # 只放整理完成的正式 JSON
```

強制規則：

- 題目來源只使用 `question_sources` 中的 PDF 或從這些 PDF 提取的文字。
- 正式 CLF 題庫只輸出到 `questions/clf_Q起始-Q結束.json`。
- 所有 `clf_` JSON 只同步至 Supabase `questions` table，不可寫入 `saa_questions`。
- `questions` 資料夾只允許放完成整理的題庫 JSON。
- 不產生 Markdown 題目表格、Excel、CSV 或其他中繼格式。
- 每個 JSON 檔案最多 30 題。

---

## 1. 決定本次要從哪一題開始

開始整理前，先掃描 `questions/clf_Q*-Q*.json`，不能只依檔名猜測最後題號。

依序執行：

1. 讀取每個 JSON 的 `questions` 陣列。
2. 收集所有 `question_no`。
3. 確認題號從 Q1 開始、沒有重複、沒有跳號。
4. 找出最大的 `question_no`。
5. 下一題固定為「最大題號 + 1」。

範例：

- 資料夾最後一題是 Q10 → 下一批從 Q11 開始。
- 資料夾最後一題是 Q20 → 下一批從 Q21 開始。
- 資料夾是空的 → 從 Q1 開始。
- 若現有檔案缺少 Q15 → 先停止產題並指出缺少 Q15，不可直接從 Q21 繼續。

可執行以下指令驗證現有題庫：

```bash
npm run validate:questions:clf
```

預期輸出範例：

```text
Local JSON validation completed for clf: questions=30, latest=Q30
```

---

## 2. 根據題號選擇 PDF

- `with_aizh`：題目、雙語內容、官方答案與選項解析的主要來源。
- `with_discussion`：社群投票、熱門留言與爭議觀點的輔助來源。
- 題數是實際掃描各分檔中 `Question #` 題目標題後計算的唯一題號數量，不是用頁數估算。
- 「第一題／最後一題」是供 AI 搜尋用的緩衝範圍：實際第一題減 2、實際最後一題加 2，最低不小於 Q0、最高不超過 Q719；「題數」仍保留該 PDF 實際包含的題數。

## 2.1 with_aizh 對照表

| PDF | 第一題 | 最後一題 | 題數 |
| :--- | :---: | :---: | ---: |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_01.pdf` | Q0 | Q74 | 72 |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_02.pdf` | Q71 | Q146 | 72 |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_03.pdf` | Q143 | Q218 | 72 |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_04.pdf` | Q215 | Q290 | 72 |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_05.pdf` | Q287 | Q362 | 72 |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_06.pdf` | Q359 | Q434 | 72 |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_07.pdf` | Q431 | Q506 | 72 |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_08.pdf` | Q503 | Q578 | 72 |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_09.pdf` | Q575 | Q650 | 72 |
| `AWS Certified Cloud Practitioner CLF-C02_with_aizh_part_10.pdf` | Q647 | Q719 | 71 |
| **合計** | **Q0** | **Q719** | **719** |

## 2.2 with_discussion 對照表

| PDF | 第一題 | 最後一題 | 題數 | 邊界備註 |
| :--- | :---: | :---: | ---: | :--- |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_01.pdf` | Q0 | Q43 | 41 | － |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_02.pdf` | Q40 | Q92 | 49 | － |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_03.pdf` | Q89 | Q140 | 48 | － |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_04.pdf` | Q137 | Q210 | 70 | － |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_05.pdf` | Q207 | Q279 | 69 | － |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_06.pdf` | Q276 | Q345 | 66 | 第 1 頁含 Q277 討論續頁 |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_07.pdf` | Q342 | Q431 | 86 | － |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_08.pdf` | Q428 | Q530 | 99 | － |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_09.pdf` | Q527 | Q625 | 95 | － |
| `AWS Certified Cloud Practitioner CLF-C02_with_discussion_part_10.pdf` | Q622 | Q719 | 96 | － |
| **合計** | **Q0** | **Q719** | **719** | － |

## 使用方式

1. 先依題號從 2.1 找到主要 `with_aizh` PDF。
2. 再從 2.2 找到相同題號的 `with_discussion` PDF。
3. 題目位於分檔邊界時，同時查看前後兩份，避免題幹或討論被切頁截斷。
4. 每題必須以 `with_aizh` 建立內容，再用 `with_discussion` 補充社群投票與觀點。

範圍有重疊是正常的。若題目位於交界處，必須同時查看前後分檔，優先採用文字完整且沒有被截斷的內容。

範例：整理 Q70-Q80 時，`with_aizh_part_01` 可涵蓋整段；`with_discussion` 則需查看 `part_01` 與 `part_02` 的交界內容。

---

## 3. 從 PDF 擷取本批題目

每批最多處理 30 題，例如 Q1-Q30。不要一次整理過多題目。

擷取時依序完成：

1. 在兩份來源搜尋 `Question #題號` 或 `Question 題號`。
2. 擷取從該題標題開始，到下一題標題之前的完整內容。
3. 跨頁題目必須合併，不能因換頁漏掉選項、答案或討論。
4. `Most Voted`、投票比例和留言不可混進題幹或選項。
5. 淘寶、閒魚、微信、網站連結、帳號與其他廣告一律刪除。
6. 若 PDF 文字解析不完整，可使用 `pdfplumber` 重新提取相關頁面。

可選擇把原始文字存到：

```text
question_sources/clf_questions_1-30_raw/question_001.txt
```

原始文字只是暫存資料，不能放進 `questions`。

---

## 4. 逐題建立工作筆記

在寫入 JSON 前，先為每題確認以下內容。這份工作筆記不需要輸出成正式檔案。

```text
題號：
領域：
英文題幹：
繁中題幹：
選項代號：
官方答案：
單選或複選：
各選項技術判斷：
社群投票：
熱門討論重點：
來源是否有缺字或衝突：
```

判斷順序：

1. 以 `with_aizh` 的 `Correct Answer` 作為答案起點。
2. 使用題目需求與 AWS 技術原理驗證答案是否合理。
3. 使用 `with_discussion` 確認社群投票及爭議點。
4. 若兩個來源衝突，不可盲目採用最高票；必須依 AWS 原理判斷，並在 `discussion` 說明爭議。
5. 不得自行捏造來源沒有提供的投票百分比。

---

## 5. 選擇考試領域

`domain` 必須完全使用以下四個值之一：

- `領域 1：雲端概念 (Cloud Concepts)`
- `領域 2：安全與合規 (Security and Compliance)`
- `領域 3：雲端技術與服務 (Cloud Technology and Services)`
- `領域 4：計費、定價與支援 (Billing, Pricing, and Support)`

判斷提示：

- AWS 雲端價值、共享責任、雲端經濟效益、高可用性、彈性與敏捷性 → 領域 1
- IAM、最低權限、加密、合規、治理、稽核、AWS Artifact 與安全服務 → 領域 2
- 運算、儲存、資料庫、網路、分析、AI/ML、部署及其他 AWS 核心服務 → 領域 3
- 定價模型、成本管理、AWS Budgets、Cost Explorer、Support plans 與技術支援資源 → 領域 4

若同時涉及多個領域，選擇題目的主要考點，而不是只看出現的 AWS 服務名稱。

---

## 6. 產生正式 JSON

最外層固定為：

```json
{
  "exam": "AWS CLF-C02",
  "questions": []
}
```

每題固定使用以下 schema：

```json
{
  "question_no": 11,
  "domain": "領域 1：雲端概念 (Cloud Concepts)",
  "question_text": {
    "zh": "完整繁體中文題幹",
    "en": "Complete English question"
  },
  "options": {
    "A": {"zh": "繁體中文選項 A", "en": "English option A"},
    "B": {"zh": "繁體中文選項 B", "en": "English option B"},
    "C": {"zh": "繁體中文選項 C", "en": "English option C"},
    "D": {"zh": "繁體中文選項 D", "en": "English option D"}
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
    "zh": "B. 完整繁體中文選項",
    "en": "B. Complete English option"
  },
  "discussion": {
    "zh": "社群投票與考點摘要。",
    "en": "Community vote and key concept summary."
  }
}
```

複選題使用相同 schema，但 `selection_type` 必須是 `複選`，`correct_answers` 必須列出全部正確選項。完整範本：

```json
{
  "question_no": 12,
  "domain": "領域 2：安全與合規 (Security and Compliance)",
  "question_text": {
    "zh": "一家公司需要提升工作負載的安全性。解決方案架構師應選擇哪兩項措施？（選擇兩項。）",
    "en": "A company needs to improve the security of its workload. Which TWO actions should a solutions architect take? (Choose two.)"
  },
  "options": {
    "A": {"zh": "啟用靜態資料加密", "en": "Enable encryption at rest"},
    "B": {"zh": "在安全群組中允許所有連入流量", "en": "Allow all inbound traffic in the security group"},
    "C": {"zh": "使用 AWS Secrets Manager 管理憑證", "en": "Use AWS Secrets Manager to manage credentials"},
    "D": {"zh": "將管理員憑證直接儲存在應用程式程式碼中", "en": "Store administrator credentials directly in the application code"}
  },
  "option_explanations": {
    "A": {"zh": "正確。靜態資料加密可降低儲存媒體或資料快照外洩時的風險。", "en": "Correct. Encryption at rest reduces risk if storage media or data snapshots are exposed."},
    "B": {"zh": "錯誤。允許所有連入流量違反最低權限原則，會增加工作負載的攻擊面。", "en": "Incorrect. Allowing all inbound traffic violates least privilege and increases the workload's attack surface."},
    "C": {"zh": "正確。AWS Secrets Manager 可集中保護、擷取及輪替應用程式憑證。", "en": "Correct. AWS Secrets Manager centrally protects, retrieves, and rotates application credentials."},
    "D": {"zh": "錯誤。將管理員憑證寫入程式碼可能造成憑證外洩，也難以安全輪替。", "en": "Incorrect. Embedding administrator credentials in code can expose the credentials and makes secure rotation difficult."}
  },
  "selection_type": "複選",
  "correct_answers": ["A", "C"],
  "answer_text": {
    "zh": "A. 啟用靜態資料加密；C. 使用 AWS Secrets Manager 管理憑證",
    "en": "A. Enable encryption at rest; C. Use AWS Secrets Manager to manage credentials"
  },
  "discussion": {
    "zh": "社群投票與考點摘要：應同時保護靜態資料與應用程式憑證，並遵循最低權限原則。",
    "en": "Community vote and key concept summary: Protect both data at rest and application credentials, and follow the principle of least privilege."
  }
}
```

### 6.1 通用 JSON 規則

- 輸出必須是合法 UTF-8 JSON。
- 不要在正式檔案外包 Markdown code fence。
- 所有 key 必須與 schema 完全一致，不可自行改名。
- 所有字串必須是單行，不可包含實際換行或 `\n`。
- 不可輸出空字串、空物件、`null`、`N/A`、`TODO` 或省略號佔位。
- 選項代號依原題使用 A-D；原題有 E/F 時必須完整保留。
- `options` 與 `option_explanations` 的選項代號必須完全相同。

### 6.2 `question_no`

- 必須是正整數，不是字串。
- 題號必須連續、不可重複或跳號。
- 必須與檔名範圍一致。

### 6.3 `question_text`

- 只放情境描述與提問句。
- 禁止混入選項、答案、投票、留言或 `Most Voted`。
- `zh` 必須是完整繁體中文；`en` 必須是完整英文。
- 若來源缺少其中一種語言，必須翻譯補齊。

### 6.4 `options`

- 只放選項本身，不放解析、答案標記或投票。
- 每個選項都必須同時有非空的 `zh` 與 `en`。
- `zh` 使用繁體中文；`en` 使用英文。
- AWS 官方產品名稱、API、政策鍵與技術識別字可保留原文，例如 `Amazon S3`、`aws:PrincipalOrgID`。
- 除必要的官方名稱與識別字外，`zh` 不可直接貼入完整英文句子。
- 若來源只有一種語言，必須翻譯補齊另一種語言。

### 6.5 `option_explanations`

每個選項都必須有獨立、完整的雙語解析。

1. `zh` 只能使用繁體中文解析。除 AWS 官方名稱、API 和技術識別字外，不可混入英文選項原句。
2. `en` 只能使用完整英文解析，不可混入中文。
3. `zh` 與 `en` 必須能各自獨立閱讀，不可只翻譯一半或互相依賴。
4. 若來源缺少其中一種語言，必須依另一種語言翻譯補齊。
5. `options` 出現的每個選項都必須有解析，兩種語言皆不可為空。
6. 解析只放技術原理、需求符合度、缺陷與 AWS 最佳實踐。
7. 不可先重複貼上選項原文，再開始解析。
8. 不可混入投票、`Most Voted`、答案列表、留言帳號或廣告。
9. 正確選項的 `zh` 必須以「正確。」開頭，`en` 必須以 `Correct.` 開頭。
10. 錯誤選項的 `zh` 必須以「錯誤。」開頭，`en` 必須以 `Incorrect.` 開頭。

解析內容要求：

- 正確選項：說明技術原理、為何符合題目需求、對應的 AWS 最佳實踐。
- 錯誤選項：明確說明不符合哪一項需求、技術限制及可能問題。
- PDF 解析有缺字時，必須依題目、英文內容與 AWS 知識補成完整句子。
- 不可把多個選項的分析合併到同一個選項。

### 6.6 `selection_type` 與 `correct_answers`

- 一個正確答案 → `selection_type` 為 `單選`。
- 兩個以上正確答案 → `selection_type` 為 `複選`。
- `correct_answers` 只放選項代號陣列，例如 `["B"]` 或 `["A", "E"]`。
- 答案代號必須存在於 `options`，不可重複，並依字母順序排列。

### 6.7 `answer_text`

- 必須包含答案代號與完整選項文字。
- `zh` 使用繁體中文選項；`en` 使用英文選項。
- 複選題必須列出全部答案，例如 `A. ...，E. ...`。
- 內容必須與 `correct_answers` 和 `options` 完全一致。

### 6.8 `discussion`

- 包含社群投票結果、熱門討論重點與考點摘要。
- `zh` 是完整繁體中文；`en` 是完整英文。
- 英文留言必須翻譯成繁體中文摘要，不能直接整段貼進 `zh`。
- 投票百分比必須忠於 PDF；若頁面只顯示 `Other` 或加總不滿 100%，如實描述，不可自行補數字。
- 沒有投票資料時，明確寫出來源未提供投票比例，再提供實質考點摘要。
- 若社群答案與官方答案有爭議，簡要說明爭議原因與最終技術判斷。

---

## 7. 修正 OCR 與清除雜訊

PDF 中文可能是簡體字、錯誤部件字或 OCR 缺字。輸出前必須對照英文修正為自然、完整的繁體中文。

常見 OCR 修正：

```text
辜→遷  辴→適  迾→錯  辡→運  迀→速  辥→這  迖→部  辦→進
辯→連  辧→遠  迡→重  迗→都  迌→還  迧→針  迚→配  辢→近
辪→遲  達→通  闢→過  輓→間  輦→限  輐→問  輥→降  輵→難
輲→障  輰→隔  畹→離  轠→額  轔→邊  轈→靠  轇→非  軫→高
轀→需  迺→銷  迣→量  輍→門  轄→露  迂→邏  辷→選  轒→項
轞→題

栫→球  棕→源  棺→然  欒→案  栬→理  梔→沒  桟→模  栺→格
械→流  桌→檢  梳→測  棬→靈  梮→活  櫟→特  栞→率  桯→步
椹→生  棯→點  棓→潰  櫨→物  榿→歡

孰→家  孀→戶  孂→所  孩→實  孥→定  孍→執  孎→擴  宛→展
孞→安  宂→將  宅→小  宆→少  宨→工  寈→並  寑→庫  寡→開
寠→建  寰→彈  宔→層  孾→導  宭→己  寳→當  寧→引  寢→異
寴→適  寵→審  宮→已  宿→幫  寀→常  孠→完  嬹→成  嬚→穩
嬦→情  寏→式  孆→才  孚→它

甠→用  畧→確  疥→符  疇→移  甤→電  痡→群  痢→細  畿→種
昀→最  疫→答  痺→編  痙→係  甅→置  甹→的  畉→目  疨→等
疙→立  甪→留  疲→管  癧→策

害→送  軸→驗  框→桶  栆→片  邇→鐘  宜→屬  梇→匯  甫→略
甉→群  畝→知  甑→者
```

強制清除：

- 淘寶、閒魚、鹹魚、微信、wechat、Taobao、xianyu、goofish.com。
- 商店名稱、帳號、促銷文字、認證代考或題庫廣告。
- 留言者名稱、發文時間、upvote 次數等不影響技術判斷的資訊。
- 重複的選項文字、頁首頁尾與 PDF 日期浮水印。

遇到不在對照表內的亂碼時，使用同題英文原文與上下文重建正確繁體中文，不能保留明顯亂碼。

---

## 8. 分檔與命名

每個檔案最多 30 題，檔名必須精確反映內容範圍。

範例：

```text
clf_Q1-Q30.json
clf_Q31-Q60.json
clf_Q61-Q90.json
```

若要求整理 Q111-Q180，必須拆成：

```text
questions/clf_Q111-Q140.json
questions/clf_Q141-Q170.json
questions/clf_Q171-Q180.json
```

每個檔案都必須：

- 是可獨立解析的完整 JSON 物件。
- 包含正確的 `exam` 與 `questions`。
- 題號與檔名完全一致。
- 內部題號連續且升冪排列。

---

## 9. 完成後執行驗證

全部檔案寫入後，先執行本機驗證：

```bash
npm run validate:questions:clf
```

驗證失敗時，根據錯誤訊息回到對應題號修正，然後重新執行，直到成功。

驗證通過後，CLF JSON 會由 GitHub Actions 每日排程或檔案 push 觸發增量同步至 Supabase `questions` table。需要手動同步時使用：

```bash
npm run sync:questions:clf
```

同步程式只新增 Supabase 最大 `question_no` 後方的連續新題，不覆寫既有題目；缺號時必須停止並先補齊。

另外人工檢查：

- [ ] 題數、起始題號與結束題號正確。
- [ ] 沒有重複或跳號。
- [ ] JSON 可解析，沒有多餘文字。
- [ ] 題幹、選項、解析、答案與討論都有 `zh`、`en`。
- [ ] 繁體中文自然完整，沒有簡體字或 OCR 亂碼。
- [ ] 英文內容完整，不是空字串或佔位。
- [ ] 每個選項都有獨立解析。
- [ ] 正確答案、解析開頭與 `correct_answers` 一致。
- [ ] 投票比例忠於來源，沒有捏造缺失百分比。
- [ ] 沒有廣告、帳號、網址或 `Most Voted` 混入正式內容。

---

## 10. AI 最終回報格式

完成所有檔案與驗證後，只需簡潔回報：

```text
已完成 Q1-Q30。
輸出：questions/clf_Q1-Q30.json
題數：30
答案序列：A, C, ...
驗證：通過，latest=Q30
```

若來源缺頁、找不到某題或兩份 PDF 都沒有足夠內容，必須指出確切題號與缺少的資料，不可用虛構內容填補。

---

## 快速任務指令：自動接續 30 題

若不需要指定較長範圍，只想從現有題庫後面自動接續一批 30 題，可直接使用：

```text
完整讀取 question_sources/prompt_clf.md，依照所有步驟執行。
先掃描 questions 內全部 clf_Q*-Q*.json，找出最後一個 question_no，接著從下一題開始整理 30 題。
同時參考對應的 with_aizh 與 with_discussion PDF，輸出到 questions/clf_Q起始-Q結束.json；每檔最多 30 題。
修正繁體中文、OCR 亂碼與雙語解析，移除所有廣告，最後執行 npm run validate:questions:clf，直到驗證通過。CLF 檔案後續只同步至 Supabase questions table。
```
