# AWS CLF-C02 題庫整理操作手冊

這份文件是 AWS Cloud Practitioner CLF-C02 的題庫整理指令，並記錄兩種 PDF 來源的分檔題號。

除了考試名稱、PDF 檔名、題號上限、檔名前綴、每檔題數與下方對照表之外，所有 JSON schema、雙語內容、解析品質、增量接續及驗證邏輯都與 `question_sources/prompt_saa.md` 完全相同。執行 CLF 任務時必須先完整讀取 `prompt_saa.md` 的共用規則，再使用本文件的 CLF PDF 與題號對照表；JSON 的 `exam` 必須使用 `AWS CLF-C02`，不可寫成 SAA-C03。CLF 每個 JSON 最多 30 題，檔名固定使用 `clf_` 前綴。

## 快速開始：指定題號範圍

把下面指令中的 `Q11-Q100` 換成這次要整理的完整範圍，然後直接交給 AI：

```text
完整讀取 question_sources/prompt_clf.md 與 question_sources/prompt_saa.md，沿用 SAA prompt 的全部 JSON schema、品質、分檔、增量與驗證規則，整理 AWS CLF-C02 的 Q11-Q100。
Q11-Q100 是本次要完成的總範圍；每個 JSON 最多 30 題，請自動連續拆檔，不可把 90 題寫進同一個檔案。
開始前先掃描 questions/clf_Q*-Q*.json 內的 question_no，確認指定的第一題等於現有最後一題加 1，且既有題號沒有重複或缺漏；不符合時停止並回報。
同時查閱 prompt_clf.md 對照表中題號對應的 with_aizh 與 with_discussion PDF，實際建立所有 JSON 檔案，最後執行 npm run validate:questions:clf，修正到驗證通過。
所有 JSON 的 exam 必須是 AWS CLF-C02。不要只說明做法、不要只產生範例，也不要每完成一批就詢問是否繼續。
```

例如指定 `Q11-Q100` 時，必須自動拆成以下範圍：

```text
questions/clf_Q11-Q40.json
questions/clf_Q41-Q70.json
questions/clf_Q71-Q100.json
```

指定範圍規則：

- 格式固定為 `clf_Q起始題號-Q結束題號.json`，例如 `clf_Q101-Q160.json`。
- 起始題號必須接在現有正式 CLF 題庫最後一題之後，不能覆蓋或跳過既有題目。
- 結束題號可以不是 30 的倍數；最後一檔只放剩餘題目。
- CLF-C02 可指定的最高題號是 Q719。

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
