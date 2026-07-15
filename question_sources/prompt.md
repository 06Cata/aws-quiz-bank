# AWS SAA-C03 考題整理 Prompt

## PDF 切分對照表

### with_aizh（含 AI 中文翻譯 + 選項解析，共 2124 頁）

| 檔案 | 第一題 | 最後一題 |
| :--- | :--- | :--- |
| AWS_SAA-C03_with_aizh_part_01.pdf | Q1 | Q107 |
| AWS_SAA-C03_with_aizh_part_02.pdf | Q104 | Q210 |
| AWS_SAA-C03_with_aizh_part_03.pdf | Q207 | Q312 |
| AWS_SAA-C03_with_aizh_part_04.pdf | Q309 | Q414 |
| AWS_SAA-C03_with_aizh_part_05.pdf | Q411 | Q515 |
| AWS_SAA-C03_with_aizh_part_06.pdf | Q512 | Q619 |
| AWS_SAA-C03_with_aizh_part_07.pdf | Q616 | Q723 |
| AWS_SAA-C03_with_aizh_part_08.pdf | Q720 | Q824 |
| AWS_SAA-C03_with_aizh_part_09.pdf | Q821 | Q926 |
| AWS_SAA-C03_with_aizh_part_10.pdf | Q923 | Q1019 |

### with_discussion（含社群討論 + 投票結果，共 2479 頁）

| 檔案 | 第一題 | 最後一題 |
| :--- | :--- | :--- |
| AWS_SAA-C03_with_discussion_1.pdf | Q1 | Q82 |
| AWS_SAA-C03_with_discussion_2.pdf | Q79 | Q161 |
| AWS_SAA-C03_with_discussion_3.pdf | Q158 | Q241 |
| AWS_SAA-C03_with_discussion_4.pdf | Q238 | Q334 |
| AWS_SAA-C03_with_discussion_5.pdf | Q331 | Q434 |
| AWS_SAA-C03_with_discussion_6.pdf | Q431 | Q538 |
| AWS_SAA-C03_with_discussion_7.pdf | Q535 | Q647 |
| AWS_SAA-C03_with_discussion_8.pdf | Q644 | Q768 |
| AWS_SAA-C03_with_discussion_9.pdf | Q765 | Q892 |
| AWS_SAA-C03_with_discussion_10.pdf | Q889 | Q1019 |

---

## 整理流程

### 目標

將 PDF 考題提取並整理成結構化 JSON，同時參考兩種來源：
- **with_aizh**（主）→ 題目、選項、中英文翻譯、各選項解析
- **with_discussion**（輔）→ 社群投票百分比、討論觀點

### 步驟

```
1. 查表 → 確認題號範圍對應哪些 PDF part 檔案
2. 提取 → 執行腳本從 PDF 提取原始文字，儲存到 questions_XX-XX_raw/
3. 整理 → AI 讀取原始檔案，整理成 JSON
4. 輸出 → 產出 QXX-QXX.json
   - 若超過 10 題，自動切分為多個檔案（每檔最多 10 題）
   - 命名規則：Q111-Q120.json、Q121-Q130.json
5. 檢查 → 題數完整、答案正確、解析合理
```

### 範例：整理 Q90-Q150

查表後需要的檔案：
- `AWS_SAA-C03_with_aizh_part_01.pdf`（涵蓋 Q90~Q107）
- `AWS_SAA-C03_with_aizh_part_02.pdf`（涵蓋 Q108~Q150）
- `AWS_SAA-C03_with_discussion_2.pdf`（涵蓋 Q90~Q150）

---

## 快速使用指令（複製貼上給 AI）

```
讀取 prompt.md，幫我整理 Q___-Q___ 題成 JSON。
參考檔案：
- C:\Users\639657\Desktop\AI_Tool\aws_pdf\AWS_SAA-C03_with_aizh_part_XX.pdf
- C:\Users\639657\Desktop\AI_Tool\aws_pdf\AWS_SAA-C03_with_discussion_X.pdf
不能有缺漏。
```

---

## 提取腳本（一鍵提取 + 儲存原始內容）

**安裝：** `pip install pdfplumber`

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AWS SAA-C03 考題提取腳本（含 OCR 亂碼自動修正）
用法: python extract_pdf_questions.py
修改下方設定區域的 pdf_path、start_num、end_num 即可
"""
import pdfplumber
import re
import os

# ===== OCR 亂碼對照表 =====
OCR_FIX_MAP = {
    # 辶/辵 部首系列
    '辜': '遷', '辴': '適', '迾': '錯', '辡': '運', '迀': '速',
    '辥': '這', '迖': '部', '辦': '進', '辯': '連', '辧': '遠',
    '迡': '重', '迗': '都', '迌': '還', '迧': '針', '迚': '配',
    '辢': '近', '辪': '遲', '達': '通', '闢': '過', '輓': '間',
    '輦': '限', '輐': '問', '輥': '降', '輵': '難', '輲': '障',
    '輰': '隔', '畹': '離', '轠': '額', '轔': '邊', '轈': '靠',
    '轇': '非', '軫': '高', '轀': '需', '迺': '銷', '迣': '量',
    '輍': '門', '轄': '露', '迂': '邏', '辷': '選', '轒': '項',
    '轞': '題',
    # 木 部首系列
    '栫': '球', '棕': '源', '棺': '然', '欒': '案', '栬': '理',
    '梔': '沒', '桟': '模', '栺': '格', '械': '流', '桌': '檢',
    '梳': '測', '棬': '靈', '梮': '活', '櫟': '特', '栞': '率',
    '桯': '步', '椹': '生', '棯': '點', '棓': '潰', '櫨': '物',
    '榿': '歡',
    # 宀/子 部首系列
    '孰': '家', '孀': '戶', '孂': '所', '孩': '實', '孥': '定',
    '孍': '執', '孎': '擴', '宛': '展', '孞': '安', '宂': '將',
    '宅': '小', '宆': '少', '宨': '工', '寈': '並', '寑': '庫',
    '寡': '開', '寠': '建', '寰': '彈', '宔': '層', '孾': '導',
    '宭': '己', '寳': '當', '寧': '引', '寢': '異', '寴': '適',
    '寵': '審', '宮': '已', '宿': '幫', '寀': '常', '孠': '完',
    '嬹': '成', '嬚': '穩', '嬦': '情', '寏': '式', '孆': '才',
    '孚': '它',
    # 田/疒 部首系列
    '甠': '用', '畧': '確', '疥': '符', '疇': '移', '甤': '電',
    '痡': '群', '痢': '細', '畿': '種', '昀': '最', '疫': '答',
    '痺': '編', '痙': '係', '甅': '置', '甹': '的', '畉': '目',
    '疨': '等', '疙': '立', '甪': '留', '疲': '管', '癧': '策',
    # 其他
    '害': '送', '軸': '驗', '框': '桶', '栆': '片', '邇': '鐘',
    '宜': '屬', '梇': '匯', '甫': '略', '甉': '群', '畝': '知',
    '甑': '者',
}

def fix_ocr(text):
    """套用 OCR 亂碼修正"""
    for wrong, correct in OCR_FIX_MAP.items():
        text = text.replace(wrong, correct)
    return text

def main():
    # ===== 設定區域（修改這裡即可） =====
    pdf_path = r"C:\Users\639657\Desktop\AI_Tool\aws_pdf\AWS_SAA-C03_with_aizh_part_01.pdf"
    start_num = 90
    end_num = 100
    # ===================================

    output_dir = f"questions_{start_num}-{end_num}_raw"

    print("=" * 60)
    print("AWS SAA-C03 考題提取工具（含 OCR 亂碼修正）")
    print("=" * 60)
    print(f"來源: {pdf_path}")
    print(f"範圍: Question #{start_num} ~ #{end_num}\n")

    # 1. 提取 PDF 全文
    text_content = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"PDF 總頁數: {total_pages}")
        for i, page in enumerate(pdf.pages, 1):
            if i % 20 == 0:
                print(f"  讀取進度: {i}/{total_pages}")
            text = page.extract_text()
            if text:
                text_content.append(text)

    content = '\n'.join(text_content)
    print(f"提取完成，總字數: {len(content):,}")

    # 2. 套用 OCR 亂碼修正
    content = fix_ocr(content)
    print(f"OCR 亂碼修正完成（{len(OCR_FIX_MAP)} 組替換規則）")

    # 3. 搜尋題目位置
    print(f"\n搜尋題目 #{start_num}-#{end_num}...")
    questions = {}
    for num in range(start_num, end_num + 1):
        for pattern in [rf"Question\s*#\s*{num}\b", rf"Question\s+{num}\b"]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                questions[num] = match.start()
                print(f"  ✓ Q{num}")
                break
        if num not in questions:
            print(f"  ✗ Q{num} 未找到")

    # 4. 儲存修正後的原始內容
    if questions:
        os.makedirs(output_dir, exist_ok=True)
        sorted_items = sorted(questions.items())
        for idx, (q_num, start_pos) in enumerate(sorted_items):
            end_pos = sorted_items[idx + 1][1] if idx + 1 < len(sorted_items) else start_pos + 3000
            file_path = os.path.join(output_dir, f"question_{q_num:03d}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"=== Question #{q_num} ===\n\n")
                f.write(content[start_pos:end_pos])

        print(f"\n{'=' * 60}")
        print(f"找到: {len(questions)} 題 → {sorted(questions.keys())}")
        missing = set(range(start_num, end_num + 1)) - set(questions.keys())
        if missing:
            print(f"缺少: {sorted(missing)}")
        print(f"儲存: {output_dir}/（已修正 OCR 亂碼）")
        print(f"\n下一步: 將原始內容交給 AI 整理成 JSON")
    else:
        print("\n錯誤: 未找到任何題目！請確認 PDF 檔案和題號範圍。")

if __name__ == "__main__":
    main()
```

---

## 輸出格式

> 以下「JSON 輸出格式」是唯一允許的輸出格式。

### JSON 輸出格式

- 輸出必須是合法的 UTF-8 JSON，不要加 Markdown code fence 或說明文字。
- 最外層固定為物件，題目放在 `questions` 陣列。
- 雙語欄位固定使用 `zh`（繁體中文）與 `en`（英文）。
- `options` 與 `option_explanations` 以 A-F 為 key，每個選項內含 `zh`、`en`。
- `correct_answers` 只放答案代號陣列，例如 `["B"]` 或 `["A", "E"]`。
- 所有字串值不可包含實際換行。

```json
{
  "exam": "AWS SAA-C03",
  "questions": [
    {
      "question_no": 671,
      "domain": "領域 3：設計安全架構 (Design Secure Architectures)",
      "question_text": {
        "zh": "一家計劃遷移至 AWS 雲端的公司……應選擇哪一項服務？",
        "en": "A company is planning to migrate to the AWS Cloud... Which service should it choose?"
      },
      "options": {
        "A": {"zh": "AWS Outposts", "en": "AWS Outposts"},
        "B": {"zh": "AWS Snowball Edge", "en": "AWS Snowball Edge"},
        "C": {"zh": "AWS Direct Connect", "en": "AWS Direct Connect"},
        "D": {"zh": "AWS Local Zones", "en": "AWS Local Zones"}
      },
      "option_explanations": {
        "A": {"zh": "錯誤。……", "en": "Incorrect. ..."},
        "B": {"zh": "正確。……", "en": "Correct. ..."},
        "C": {"zh": "錯誤。……", "en": "Incorrect. ..."},
        "D": {"zh": "錯誤。……", "en": "Incorrect. ..."}
      },
      "selection_type": "單選",
      "correct_answers": ["B"],
      "answer_text": {"zh": "B. AWS Snowball Edge", "en": "B. AWS Snowball Edge"},
      "discussion": {
        "zh": "社群投票：B（72%）。考點關鍵字：離線本地處理。",
        "en": "Community vote: B (72%). Key concept: offline local processing."
      }
    }
  ]
}
```

欄位規則：

- `question_no` 是正整數，並且必須與 `Q起始-Q結束.json` 的檔名範圍一致；`domain` 必須是下方四個領域之一。
- `question_text` 只放題幹，不得混入選項、答案或投票。
- 每個選項及每個解析都必須同時有非空的 `zh`、`en`。
- 中文解析以「正確。」或「錯誤。」開頭；英文以 `Correct.` 或 `Incorrect.` 開頭。
- `selection_type` 只能是 `單選` 或 `複選`，並與 `correct_answers` 數量一致。
- `answer_text` 放完整答案代號與文字；`discussion` 放投票資訊及考點摘要。

### 考試領域

- `領域 1：設計彈性架構 (Design Resilient Architectures)`
- `領域 2：設計高性能架構 (Design High-Performing Architectures)`
- `領域 3：設計安全架構 (Design Secure Architectures)`
- `領域 4：設計成本優化架構 (Design Cost-Optimized Architectures)`

### 解析原則

- 正確選項：技術原理 + 為何符合需求 + AWS 最佳實踐
- 錯誤選項：不符哪些需求 + 缺陷 + 可能問題

### 內容完整性規則

- **禁止出現空白或不完整的解析**：如果 PDF 提取的解析文字有缺漏（如服務名稱消失、句子中間斷裂、出現「保護、和。」這種明顯缺字），必須根據 AWS 專業知識自行補齊完整內容，不可原樣輸出殘缺文字。
- **所有選項都必須有解析**：即使 PDF 中某個選項沒有提供解析（如 D 選項或 E 選項為空），也必須根據題目需求和 AWS 知識自行撰寫解析。
- **禁止輸出空物件 `{}`**：解析欄位不可為空物件或空字串，每個選項都需要有實質內容。
- **禁止內容重複**：如果選項文字出現重複（如 `"Amazon S3 Standard Amazon S3 Standard"`），必須去除重複只保留一次。正確答案同理。
- **每個選項的解析必須獨立**：A 的解析只放 A 的分析，B 的解析只放 B 的分析，禁止把多個選項的分析混在同一個選項值裡。
- **社群討論不可為空佔位**：如果 PDF 中沒有投票資料（如只有 `"社群投票：。"`），必須根據正確答案和選項特性撰寫考點關鍵字摘要，不可輸出空內容。

---

## 質量檢查清單

- [ ] 題數完整，不缺漏
- [ ] JSON 格式正確
- [ ] 中英文內容完整（繁體中文）
- [ ] 正確答案與解析一致
- [ ] 社群投票百分比正確
- [ ] 考試領域分類正確

---

## 常見問題

| 問題 | 解法 |
| :--- | :--- |
| PDF 中文亂碼 | 用 pdfplumber（非 PyPDF2），輸出 UTF-8 |
| 跨多頁題目 | pdfplumber 逐頁合併，自動連接 |
| 找不到題號 | 可能在其他 part，或格式不同（Question #93 vs Question 93） |
| 一次處理太多 | 建議每次 10-20 題，避免內容過長 |
| 需要轉 docx | `pip install pdf2docx`，但 pdfplumber 直接讀 PDF 更推薦 |

---

## 檔案命名規範

`Q[起始題號]-Q[結束題號].json`

範例：`Q90-Q110.json`

**超過 10 題或 context 太大時自動切分：**
- 請求 Q111-Q140（30 題）→ 自動分為：
  - `Q111-Q120.json`（10 題）
  - `Q121-Q130.json`（10 題）
  - `Q131-Q140.json`（10 題）
- 每個檔案必須是可獨立解析的完整 JSON 物件

### 增量產題規則

1. 開始前先掃描專案根目錄 `questions/Q*-Q*.json`。
2. 解析所有檔案的 `questions` 陣列，找出最大的 `question_no`；不可只依檔名猜測。
3. 新題目必須從最大題號加 1 開始。例如最後一題是 Q20，下一個檔案必須從 `Q21-...json` 開始。
4. 新檔案的題號必須連續、不可重複或跳號，且檔名範圍必須與內容完全一致。
5. `questions` 資料夾只放整理完成的正式 JSON；PDF、原始文字與 prompt 一律放在 `question_sources`。

---

## 執行規則
- 一定要是繁體中文+英文，不能出現簡體中文
- **PDF 提取的中文內容可能有亂碼字**（因 PDF 字型編碼問題），整理時必須根據上下文和對應英文修正為正確的繁體中文。已知亂碼對照表如下，提取後直接套用替換：

**辶/辵 部首系列：**
`辜→遷`、`辴→適`、`迾→錯`、`辡→運`、`迀→速`、`辥→這`、`迖→部`、`辦→進`、`辯→連`、`辧→遠`、`迡→重`、`迗→都`、`迌→還`、`迧→針`、`迚→配`、`辢→近`、`辪→遲`、`達→通`、`闢→過`、`輓→間`、`輦→限`、`輐→問`、`輥→降`、`輵→難`、`輲→障`、`輰→隔`、`畹→離`、`轠→額`、`轔→邊`、`轈→靠`、`轇→非`、`軫→高`、`轀→需`、`迺→銷`、`迣→量`、`輍→門`、`轄→露`、`迂→邏`、`辷→選`、`轒→項`、`轞→題`

**木 部首系列：**
`栫→球`、`棕→源`、`棺→然`、`欒→案`、`栬→理`、`梔→沒`、`桟→模`、`栺→格`、`械→流`、`桌→檢`、`梳→測`、`棬→靈`、`梮→活`、`櫟→特`、`栞→率`、`桯→步`、`椹→生`、`棯→點`、`棓→潰`、`櫨→物`、`榿→歡`

**宀/子 部首系列：**
`孰→家`、`孀→戶`、`孂→所`、`孩→實`、`孥→定`、`孍→執`、`孎→擴`、`宛→展`、`孞→安`、`宂→將`、`宅→小`、`宆→少`、`宨→工`、`寈→並`、`寑→庫`、`寡→開`、`寠→建`、`寰→彈`、`宔→層`、`孾→導`、`宭→己`、`寳→當`、`寧→引`、`寢→異`、`寴→適`、`寵→審`、`宮→已`、`宿→幫`、`寀→常`、`孠→完`、`嬹→成`、`嬚→穩`、`嬦→情`、`寏→式`、`孆→才`、`孚→它`

**田/疒 部首系列：**
`甠→用`、`畧→確`、`疥→符`、`疇→移`、`甤→電`、`痡→群`、`痢→細`、`畿→種`、`昀→最`、`疫→答`、`痺→編`、`痙→係`、`甅→置`、`甹→的`、`畉→目`、`疨→等`、`疙→立`、`甪→留`、`疲→管`、`癧→策`

**其他：**
`害→送`、`軸→驗`、`框→桶`、`栆→片`、`邇→鐘`、`宜→屬`、`梇→匯`、`甫→略`、`甉→群`、`畝→知`、`甑→者`

若遇到不在表中的亂碼字，參考同題的 English 欄位翻譯出正確中文。
- **所有欄位內容必須移除廣告垃圾文**（如「鹹魚: IT認證輕鬆過」、Taobao shop、xianyu shop、wechat、goofish.com 等推銷連結或帳號資訊），僅保留與題目相關的技術解析內容
- **不須詢問是否繼續下一步，直接做完所有要求，輸出多份檔案**
- 若 context 接近上限，立即輸出當前已完成的檔案，再繼續處理下一份
- 所有檔案完成後才算任務結束
