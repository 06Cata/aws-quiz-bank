# 學習卡牌整理與新考試擴充指南

這份文件記錄 AWS Quiz Bank 目前的卡牌整理邏輯。目標是讓未來任何考試的 PDF、投影片、截圖或課程筆記，都能用同一套方法整理成 JSON，驗證後同步到獨立的 Supabase 卡牌與筆記資料表。

> 本文件負責「內容如何整理」及「新考試如何接入」。Supabase 建表、RLS 與 CLF／SAA 現有環境的完整設定，請搭配 `FLASHCARDS_SUPABASE_SETUP.md`。

## 強制規則總表

以下規則同時適用於 CLF、SAA 及未來新增的所有考試卡牌；若後續整理 PDF、投影片、截圖或題目解析，必須全部遵守。

### 內容與去重

1. 一個核心觀念只保留一張一般知識卡。
2. 相同服務不能因為定義、年份、限制、使用情境或考題問法不同而拆成重複卡牌。
3. 卡牌 `Title` 先寫服務名稱或重點答案，再寫必要補充，例如 `Standard Reserved Instances – 1- or 3-Year Commitment`。
4. 不以 `What`、`Which`、`How` 等完整考題問句作為一般知識卡標題。
5. 定義、用途、年份、付款方式、適用與不適用情境、常見考題、判斷關鍵字及陷阱全部整理進同一張卡的 `Description`。
6. 比較本身是獨立考點時才建立比較卡，例如 `ALB vs NLB`、`ELB vs ASG`、`EBS vs Instance Store`。
7. 不同且可獨立出題的觀念必須拆卡；不能為了減少張數，把整章不相關內容塞入同一張卡。
8. Description 段落過長時必須依完整句意分段，段落之間固定空一行；不得把全部解析擠成一大段。
9. `補充與常見考法：`、`常見情境與考法：`、`常見考法：` 必須另起新段，前方固定空一行；其內容太長時也要繼續分段。

### Chapter 與 Topic

1. JSON 固定使用 `chapter → topic → title → Domain/Description` 三層卡牌結構。
2. Chapter 格式固定為 `chapter數字: 章節名稱`，從 `chapter1` 開始且編號不可重複。
3. Topic 是觀念分類，不是單張投影片，也不是 PDF 頁碼。
4. Topic 不加 `01`、`02`、`03`；只有具有明確先後順序的卡牌 title 才能編號。
5. 每個 chapter 必須且只能有一個 `Shared Responsibility for <該章主題>` topic。
6. Responsibility topic 必須針對該章服務，清楚區分 AWS 的 `Security OF the Cloud` 與客戶的 `Security IN the Cloud`。

### Responsibility 與角色扮演順序

沒有角色扮演時：

```text
一般 topics
└── Shared Responsibility for <該章主題>   ← 最後
```

有角色扮演時：

```text
一般 topics
├── Shared Responsibility for <該章主題>   ← 倒數第二
└── 角色扮演：<情境名稱>                    ← 最後
```

1. 正式課程、PDF 或使用者提供的角色扮演必須保留，不可因為內容已寫進一般卡牌就刪除。
2. 角色扮演是「同一觀念一張一般卡」的保留例外：一般卡用來記憶知識，角色扮演卡用來練習整合、溝通及商業應用。
3. 一個 chapter 最多一個角色扮演 topic；其中的目標可依 `1.`、`2.`、`3.`、`4.` 編號。
4. 沒有原始角色扮演內容時，不必為了湊格式自行建立。

### JSON、考試與 Supabase

1. `flashcards_sources/<exam>_flashcards.json` 是編輯來源；`flashcards/<exam>_flashcards.json` 是正式同步版本，發布前兩者必須完全一致。
2. 每種考試使用自己的 JSON、卡牌表與筆記表，不可混用 CLF、SAA 或其他考試資料。
3. 每張卡只允許 `Domain` 與 `Description`，兩者都必須是非空字串。
4. Domain 必須使用該考試的官方考試藍圖，不可因服務相同而跨考試沿用。
5. 修改 topic 或 title 會影響 `source_key`；同步時必須保留既有卡牌 ID，避免已存筆記失聯。
6. 發布流程固定為：更新來源 JSON、複製至正式 JSON、validate、sync，再執行第二次 sync 確認零變更。
7. 驗證器會檢查每章 Responsibility 的數量與 JSON 位置；API 會保證 UI 中 Responsibility／角色扮演顯示在正確尾端順序。

## 1. 核心資料流

```text
PDF／投影片／截圖／課程筆記
              ↓
      整理章節與考試 Domain
              ↓
 flashcards_sources/<exam>_flashcards.json
              ↓
       人工檢查與 JSON 驗證
              ↓
 flashcards/<exam>_flashcards.json
              ↓
   本機同步或 GitHub Actions 同步
              ↓
 Supabase <exam>_flashcards
              ↓
        學習卡牌 UI
              ↓
 Supabase <exam>_flashcard_notes
```

兩個 JSON 目錄的用途不同：

- `flashcards_sources/`：編輯中的來源版本。
- `flashcards/`：已確認並準備同步、部署的正式版本。
- PDF 不會直接寫入 Supabase；部署只需要正式 JSON。
- GitHub Actions 目前只監看 `flashcards/`，只修改 `flashcards_sources/` 不會觸發部署同步。

## 2. 一份 JSON 對應一種考試

檔名固定為：

```text
flashcards_sources/<exam>_flashcards.json
flashcards/<exam>_flashcards.json
```

目前已內建：

| 考試代碼 | 來源 JSON | 正式 JSON | Supabase 卡牌表 | Supabase 筆記表 |
| :--- | :--- | :--- | :--- | :--- |
| `clf` | `clf_flashcards.json` | `clf_flashcards.json` | `clf_flashcards` | `clf_flashcard_notes` |
| `saa` | `saa_flashcards.json` | `saa_flashcards.json` | `saa_flashcards` | `saa_flashcard_notes` |

不同考試必須完全分流：

- 不共用卡牌資料表。
- 不共用筆記資料表。
- 不共用 JSON。
- UI 選擇哪一種考試，就只能讀取該考試的 chapter、Domain、卡牌與筆記。

## 3. JSON 的三層結構

```json
{
  "chapter1: What is Cloud Computing?": {
    "Cloud Computing Fundamentals": {
      "On-demand delivery": {
        "Domain": "領域 1：雲端概念 (Cloud Concepts)",
        "Description": "Cloud computing 透過網際網路按需要提供運算、儲存、資料庫與其他 IT 資源，並採用 pay-as-you-go 定價。"
      }
    }
  }
}
```

對應關係：

| JSON 層級／欄位 | 意義 | UI | Supabase 欄位 |
| :--- | :--- | :--- | :--- |
| `chapter1: ...` | PDF 或課程的大章節 | Chapter 下拉選單 | `chapter_key` |
| `Cloud Computing Fundamentals` | 小章節／同類觀念群組 | 卡牌的 topic | `topic` |
| `On-demand delivery` | 一張卡牌的核心觀念 | 卡牌正面主標題 | `title` |
| `Domain` | 考試藍圖中的領域 | 卡牌最上方小字 | `exam_domain` |
| `Description` | 定義、比較、情境與考試線索 | 翻牌解析 | `description` |

每張卡牌只能包含：

```json
{
  "Domain": "非空字串",
  "Description": "非空字串"
}
```

不要自行增加 `Answer`、`Source`、`Image` 或其他欄位；目前驗證器會拒絕未支援欄位。

## 4. Chapter 整理規則

Chapter 代表 PDF、課程或官方考綱中的大主題。

格式必須完全符合：

```text
chapter正整數: 章節名稱
```

正確：

```text
chapter1: What is Cloud Computing?
chapter2: AWS Identity & Access Management
chapter3: Amazon EC2
```

錯誤：

```text
content1
Chapter 01
chapter0: Introduction
chapter2 AWS IAM
```

規則：

1. 從 `chapter1` 開始。
2. 每個 chapter 編號不可重複。
3. 章節名稱要能概括內容，不要用單張投影片標題建立過多 chapter。
4. 同一項 AWS 服務的基本概念、類型、責任模型與情境題，通常留在同一 chapter，再用 topic 分組。
5. 不要因為新增一張卡牌就改既有 chapter 名稱；chapter 名稱是卡牌身分的一部分。
6. 每個 chapter 都必須有 `Shared Responsibility for <該章主題>` topic，至少清楚區分 AWS 的 `Security OF the Cloud` 與客戶的 `Security IN the Cloud`。沒有角色扮演時放在最後；有角色扮演時放在倒數第二，角色扮演固定放最後。內容必須針對該章服務撰寫，不能只重複完全相同的通用句子。

## 5. Topic 小章節整理規則

Topic 用來把同一 chapter 內的卡牌依用途分組。建議分組順序：

```text
基本概念
核心組成或關係
服務／類型比較
操作或流程
計費／安全／責任
角色扮演（該章有提供時）
```

例如 ELB 與 ASG chapter 可拆成：

```text
Scalability & Cloud Concepts
Load Balancing Fundamentals
Load Balancer Types
Auto Scaling Group Fundamentals
Auto Scaling Strategies
角色扮演：向 Priya 解釋高流量電商架構
```

規則：

1. Topic 是分類，不是一張卡牌。
2. 同一 topic 內的卡牌必須回答同一類問題。
3. 概念、服務類型、操作流程與購買方式不要全部混在同一 topic。
4. 小章節名稱不需要加 `01`、`02`、`03`。
5. 不要建立只有一張卡、但其實可合理併入既有分類的 topic。
6. Topic 改名或移動卡牌前，要先理解第 11 節的 Supabase 身分規則。
7. API 會把 `Shared Responsibility for ...` 固定排在一般 topic 之後；若有角色扮演，角色扮演再排在其後，成為 chapter 最後一個 topic。

### 5.1 每個 Chapter 的固定尾端順序

這是 CLF、SAA 與未來新考試共同遵守的強制規則：

```text
沒有角色扮演：
一般 topics
└── Shared Responsibility for <該章主題>   ← 最後

有角色扮演：
一般 topics
├── Shared Responsibility for <該章主題>   ← 倒數第二
└── 角色扮演：<情境名稱>                    ← 最後
```

詳細規則：

1. 每個 chapter 必須且只能有一個以 `Shared Responsibility for ` 開頭的 topic。
2. Responsibility topic 至少要有 AWS 與 Customer 兩個方向，清楚說明 `Security OF the Cloud` 和 `Security IN the Cloud`。
3. Responsibility 內容必須對應該章服務，例如 EC2 要寫 AWS 管底層硬體、客戶管 Guest OS 與 Security Groups；不可每章複製相同空泛文字。
4. 角色扮演不是每章必須；只有 PDF、課程或使用者提供正式角色扮演練習時才加入。
5. 一個 chapter 若有角色扮演，只建立一個角色扮演 topic，並將目標依 `1.`、`2.`、`3.`、`4.` 排列在其中。
6. 角色扮演必須保留，不可因為相關觀念已寫入一般卡牌就刪除；一般卡負責記憶知識，角色扮演卡負責練習整合與表達。
7. JSON 驗證器會檢查上述數量和位置；API 也會依此順序輸出到 UI。

目前 API 依 `chapter_order`、`topic`、`title` 排序，JSON 的插入順序不保證成為 UI 顯示順序。因此 topic 以清楚分類為主；卡牌若必須依序顯示，應依第 7 節在 title 加入數字。

## 6. 一張卡牌應該包含什麼

### 6.1 一個主要觀念只保留一張卡

整理時要同時遵守兩個方向：不同觀念要拆開，相同觀念不能因為定義、年份、使用情境或考題問法不同而重複建立卡牌。

同一 AWS 服務或核心觀念的以下資訊，全部放在同一張卡的 `Description`：

- 一句話定義與主要用途。
- 承諾期間、計費方式或必要數字。
- 適用與不適用的使用情境。
- 常見考題關鍵字、答案判斷方式與陷阱。
- 角色扮演時使用的非技術比喻或商業說法。

例如 `Dedicated Instances` 只保留一張卡，解析同時寫硬體隔離的定義、沒有 Host 層級控制、適用情境，以及考題如何和 `Dedicated Host` 區分。不要再另外建立 `Dedicated Instances – Hardware Isolation Scenario`。

投影片有五個彼此獨立、可單獨出題的觀念，才拆成五張卡，不要全部塞入一張。

例如 `What is Cloud Computing?` 可拆成：

- `On-demand delivery`
- `Pay-as-you-go pricing`
- `Right-sized resources`
- `Near-instant resource access`
- `AWS manages the underlying hardware`

如果「比較本身」是需要學會的獨立判斷能力，可以保留一張比較卡，例如：

- `ELB vs Auto Scaling Group`
- `ALB vs NLB`
- `EBS vs Instance Store`

### 6.2 Title 寫法

Title 應該：

- 短而明確。
- 優先保留 AWS 官方英文名稱。
- 對應投影片的粗體關鍵字或考題答案。
- 能單獨看出要回想的觀念。

建議：

```text
Vertical Scalability
Network Load Balancer (NLB)
AWS Responsibility – Security OF the Cloud
Customer Responsibility – Security IN the Cloud
```

避免：

```text
重點一
這個很重要
投影片第 8 頁
其他內容
```

### 6.3 Description 寫法

Description 建議依這個順序撰寫：

1. 一句話定義。
2. 主要用途或運作方式。
3. 與相似服務的差異。
4. 適用或不適用情境。
5. 常見考題關鍵字或陷阱。
6. 必要時加入商業比喻或實例。

範例：

```text
Network Load Balancer 是 Layer 4 負載平衡器，支援 TCP、UDP 與 TLS。
它適合大量連線、極高吞吐量與超低延遲的工作負載。
考題看到「大量連線、超低延遲、TCP／UDP」時選 NLB；
需要依 URL path 或 host name 路由 HTTP／HTTPS 時選 ALB。
```

Description 不應只是把 Title 換句話說，也不要加入與這張卡無關的整章內容。

#### Description 分段與空行

Description 必須以易讀性為優先，不能把定義、操作方式、比較、情境和考題全部擠在同一個長段落。

規則：

1. 一個段落只處理一組緊密相關的意思，建議不超過約 180 個字或 2～3 個完整句子。
2. 段落間在 JSON 字串中使用 `\n\n`，UI 顯示時就是一個空白行。
3. 優先在 `。`、`！`、`？`、`；` 等完整語意結束處換段，不可切斷 AWS 服務名稱、英文縮寫、數字、ARN 或程式碼。
4. 定義與核心用途放第一段；差異、限制或操作方式另起一段；考題與情境放最後。
5. `補充與常見考法：`、`常見情境與考法：`、`常見考法：` 一律另起新段，標籤前必須有 `\n\n`。
6. 標籤後的解析若仍過長，要依句意再拆成多段，不可因為已經有標籤就保留超長段落。

正確：

```text
Standard Reserved Instances 適合規格穩定、會持續運行 1 年或 3 年的工作負載，可用長期承諾換取較高折扣。

付款方式包括 No Upfront、Partial Upfront 與 All Upfront；承諾越長、預付越多，通常折扣越高。

補充與常見考法：題目只強調「持續運行 1 年」且沒有提到更換 instance family 或 OS 時，通常選 Standard Reserved Instances。

若題目強調長期使用但未來可能更換規格，則改選 Convertible Reserved Instances。
```

錯誤：

```text
把定義、年份、付款方式、適用情境、服務比較及所有考題陷阱全部連續寫在同一個很長的段落，中間完全沒有空白行。
```

### 6.4 情境與考題的放置方式

一般考題情境不是獨立知識點，不建立 `Scenario` 或 `Exam Questions` topic，也不以問題句建立另一張知識卡。常見考題仍應寫在對應觀念卡的解析末段。

正式課程提供的角色扮演練習要保留為獨立的 `角色扮演：...` topic，作為知識應用練習的例外。它不是用來取代一般觀念卡；同一情境涉及的基礎定義、年份與考題陷阱，仍要保留在相應知識卡的 `Description`。

應改寫到對應觀念卡的解析末段：

```text
常見情境與考法：應用程式會持續運行 1 或 3 年，且規格穩定時，選 Standard Reserved Instances。若題目強調未來需要更換 instance family 或 OS，則改選 Convertible Reserved Instances。
```

若一個商業情境同時涉及多個服務，角色扮演 topic 可以用目標 1、2、3、4 依序練習完整回答；一般知識區仍應拆回各服務卡。只有 `ALB vs NLB`、`ELB vs ASG` 這類「服務選擇比較」本身就是考試觀念時，才保留比較卡。

## 7. 什麼時候要編號

小章節 topic 不編號；只有卡牌具有明確順序時才編號。

需要編號：

- 建立流程。
- 政策 JSON 的逐項要素。
- 角色扮演的目標 1、2、3、4。
- 必須依序理解的生命週期。

範例：

```text
1. Explain ELB and ASG
2. Choosing ALB or NLB
3. Scaling Strategies
4. Black Friday Practical Plan
```

不需要編號：

- EC2 instance families。
- Load Balancer types。
- EC2 purchasing options。
- Classic ports。
- 沒有先後關係的平行觀念。

若超過 9 張且 UI 必須依字串排序，才使用 `01.`、`02.`；一般情況使用 `1.`、`2.`、`3.`。

## 8. PDF／投影片轉 JSON 的標準流程

### 步驟 1：先建立整份 PDF 大綱

先記錄：

- PDF 的章節名稱。
- 每章涵蓋的 AWS 服務。
- 官方考試 Domain。
- 重複出現的觀念。
- 流程圖、比較表與責任模型。
- 粗體字、標題及老師強調的考試線索。

不要看到一頁就立即建立一個 chapter。先看完整章節，再決定階層。

### 步驟 2：建立 chapter

將課程的大章節對應成：

```text
chapter1: ...
chapter2: ...
chapter3: ...
```

Chapter 編號代表學習順序，不代表 PDF 頁碼。

### 步驟 3：先分 topic，再寫卡牌

每章先用基本概念、類型、比較、流程、安全／責任、情境等方式分組。

錯誤方式：

```text
EC2
├── 所有 EC2 卡牌全部混在一起
```

建議方式：

```text
EC2
├── EC2 Fundamentals
├── EC2 Launch Configuration
├── EC2 Instance Families
├── EC2 Purchasing Options
├── Shared Responsibility for Amazon EC2
└── 角色扮演：向業務人員解釋 EC2
```

### 步驟 4：從每頁擷取可獨立測驗的觀念

看到以下內容時通常應建立卡牌：

- 官方定義。
- 粗體服務名稱。
- 數字、期間、port、Layer 或限制。
- A 與 B 的差異。
- 責任屬於 AWS 或客戶。
- 「適合什麼情境」。
- 「不支援什麼」。
- 考題答錯後顯示的解析。

### 步驟 5：合併重複內容

新增前先搜尋：

```bash
rg -n "關鍵字|服務名稱" flashcards_sources/<exam>_flashcards.json
```

如果卡牌已存在：

- 補強原 Description。
- 加入新的考題陷阱或例子。
- 不要建立名稱稍有不同、內容幾乎相同的新卡。

### 步驟 6：確認技術正確性

PDF 可能過時或為了考試而簡化。遇到以下內容應查 AWS 官方文件：

- 服務支援範圍。
- 容量、限制、折扣與保留期間。
- 服務已改名或淘汰。
- 「一定」、「只能」、「永遠」等絕對敘述。

卡牌可以保留考試線索，但 Description 應補充正確例外。

例如：

```text
ASG 不會把正在執行的 EC2 原地自動改成另一個 instance type；
但可以使用 Mixed Instances Policy，或更新 Launch Template 後用
Instance Refresh 建立新 instance 並替換舊 instance。
```

### 步驟 7：加入角色扮演情境

角色扮演應獨立成 topic，並依目標順序建立卡牌。

加入後必須重新安排 chapter 尾端順序：`Shared Responsibility for ...` 放倒數第二，角色扮演放最後。角色扮演內容不得因為與一般卡牌觀念重疊而刪除。

每張 Description 應包含：

- 對方的職位與關切。
- 非技術性的解釋。
- 與業務的實際關係。
- 風險或限制。
- 可執行的建議。

不要只複製角色設定；卡牌要直接提供可以對角色說的答案。

## 9. Domain 規則

Domain 必須使用該考試官方藍圖，不可因為 AWS 服務名稱相同就沿用另一場考試的 Domain。

例如 CLF：

```text
領域 1：雲端概念 (Cloud Concepts)
領域 2：安全與合規 (Security and Compliance)
領域 3：雲端技術與服務 (Cloud Technology and Services)
領域 4：計費、定價與支援 (Billing, Pricing, and Support)
```

新增考試前先確認：

- Domain 數量。
- Domain 正式名稱。
- 前端篩選標籤。
- 該考試是否仍為四個 Domain。

目前前端只內建 `domain_1` 到 `domain_4`。若新考試不是四個 Domain，必須同步修改前端型別與篩選邏輯，不能只修改 JSON。

## 10. 發布、驗證與同步

以下範例使用 `<exam>` 代表考試代碼。

### 10.1 編輯來源檔

```text
flashcards_sources/<exam>_flashcards.json
```

### 10.2 複製成正式檔

```bash
cp flashcards_sources/<exam>_flashcards.json flashcards/<exam>_flashcards.json
```

### 10.3 檢查 JSON

```bash
jq empty flashcards_sources/<exam>_flashcards.json
jq empty flashcards/<exam>_flashcards.json
cmp -s flashcards_sources/<exam>_flashcards.json flashcards/<exam>_flashcards.json
```

### 10.4 執行內容驗證

已有 npm script 時：

```bash
npm run validate:flashcards:<exam>
```

或直接執行：

```bash
cd apps/api
python -m app.jobs.sync_local_flashcards --exam <exam> --validate-only
```

驗證器會檢查：

- 檔案存在。
- JSON 有效。
- Chapter 格式正確。
- Chapter 編號不重複。
- Topic、Title、Domain、Description 不是空字串。
- 卡牌沒有未支援欄位。
- 卡牌身分沒有重複。

### 10.5 同步 Supabase

```bash
npm run sync:flashcards:<exam>
```

或：

```bash
cd apps/api
python -m app.jobs.sync_local_flashcards --exam <exam>
```

成功輸出範例：

```text
scanned=245, inserted=4, updated=2, skipped=239, deactivated=0
```

欄位意義：

| 統計 | 意義 |
| :--- | :--- |
| `scanned` | 本機正式 JSON 的卡牌總數 |
| `inserted` | 新增卡牌 |
| `updated` | 內容更新或安全移動 topic 的卡牌 |
| `skipped` | 內容完全相同，未寫入 |
| `deactivated` | 已從正式 JSON 移除，因此設為 inactive 的舊卡 |

同步完成後再執行一次，理想結果應為：

```text
inserted=0, updated=0, skipped=<全部卡牌>, deactivated=0
```

這代表同步具有冪等性，不會重複新增資料。

## 11. 更新、移動、改名與刪除規則

卡牌的 `source_key` 由以下內容產生：

```text
exam + chapter_key + topic + title
```

內容雜湊 `content_hash` 則包含 chapter、topic、title、Domain 與 Description。

### 11.1 只修改 Domain 或 Description

結果：

```text
updated += 1
```

`source_key` 與 Supabase `id` 不變，既有使用者筆記保留。

### 11.2 在同一 chapter 內移動到另一個 topic

目前同步器會用相同的：

```text
chapter_key + title
```

辨識這是同一張卡，直接更新既有資料列，保留 Supabase `id` 與使用者筆記。

前提是同一 chapter 內只有一張相同 title 的 active 卡牌。

### 11.3 修改 title 或 chapter_key

這會改變卡牌身分，而且目前無法自動確認新舊卡是否為同一張。

可能結果：

- 新名稱被視為 inserted。
- 舊名稱被設為 deactivated。
- 原本綁定舊 `flashcard_id` 的筆記不會顯示在新卡。

因此：

1. 已發布卡牌不要只為了美觀任意改 title 或 chapter 名稱。
2. 確定要改名時，應先設計資料庫 migration，將舊資料列更新成新身分。
3. 不要直接刪除 Supabase 舊卡或筆記資料。

### 11.4 從 JSON 刪除卡牌

同步器不會硬刪資料，而是：

```text
is_active = false
```

網站只讀取 active 卡牌，所以該卡與其筆記暫時不顯示；資料仍保留在 Supabase。

若之後使用完全相同的 chapter、topic、title 重新加入，原資料列會重新啟用。

## 12. 新增第三種考試

目前程式只內建 `clf` 與 `saa`。新增例如 `soa` 時，不能只建立 `soa_flashcards.json`，必須完成以下項目。

### 12.1 建立 JSON

```text
flashcards_sources/soa_flashcards.json
flashcards/soa_flashcards.json
```

### 12.2 建立獨立 Supabase 表

先把下方 `<exam>` 全部替換成實際小寫代碼：

```sql
create table public.<exam>_flashcards (
  id uuid primary key default gen_random_uuid(),
  source_key text not null unique,
  chapter_key text not null,
  chapter_order integer not null check (chapter_order > 0),
  topic text not null,
  title text not null,
  exam_domain text not null,
  description text not null,
  content_hash text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.<exam>_flashcard_notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  flashcard_id uuid not null
    references public.<exam>_flashcards(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_id, flashcard_id)
);

create index <exam>_flashcards_chapter_idx
  on public.<exam>_flashcards (chapter_order, topic)
  where is_active = true;

create index <exam>_flashcards_domain_idx
  on public.<exam>_flashcards (exam_domain)
  where is_active = true;

create index <exam>_flashcard_notes_user_idx
  on public.<exam>_flashcard_notes (user_id, created_at desc);
```

接著依 `FLASHCARDS_SUPABASE_SETUP.md` 的模式啟用 RLS，建立：

- 登入使用者只能讀取 active 卡牌。
- 使用者只能讀取、加入、刪除自己的筆記。
- 前端使用者不能直接新增、修改或刪除正式卡牌。

### 12.3 更新後端白名單

需要修改：

1. `apps/api/app/services/local_flashcards.py`
   - 把新代碼加入 `EXAMS`。
2. `apps/api/app/jobs/sync_local_flashcards.py`
   - 在 `get_sync_target()` 加入新代碼與卡牌表。
   - 在 CLI `choices` 加入新代碼。
3. `apps/api/app/services/supabase.py`
   - 在 `FLASHCARD_TABLES` 加入卡牌表與筆記表。
4. `apps/api/app/api/flashcards.py`
   - 建立新 router。
   - 呼叫 `register_routes(new_router, "<exam>")`。
5. `apps/api/app/main.py`
   - 掛載新 router 與獨立 API prefix。

所有資料表名稱必須由程式白名單決定，不可讓使用者從 URL 任意指定 Supabase table。

### 12.4 更新前端

修改：

```text
apps/web/src/lib/flashcards.ts
```

需要：

- 把新考試代碼加入 `FlashcardExam`。
- 在 `FLASHCARD_EXAMS` 加入名稱、短名稱、API prefix 與 Domains。
- 若 Domain 超過四個，擴充 `FlashcardDomainKey` 與 `flashcardDomainKey()`。

### 12.5 新增 npm scripts

在根目錄 `package.json` 新增：

```json
{
  "validate:flashcards:<exam>": "cd apps/api && python -m app.jobs.sync_local_flashcards --exam <exam> --validate-only",
  "sync:flashcards:<exam>": "cd apps/api && python -m app.jobs.sync_local_flashcards --exam <exam>"
}
```

### 12.6 更新 GitHub Actions

修改：

```text
.github/workflows/sync-local-flashcards.yml
```

加入：

- `flashcards/<exam>_flashcards.json` 監看路徑。
- matrix 中的新考試代碼。

### 12.7 完整驗收

至少確認：

1. 來源與正式 JSON 完全一致。
2. `validate-only` 成功。
3. 第一次同步只新增新考試卡牌。
4. 第二次同步全部 skipped。
5. UI 能切到新考試。
6. 新考試只顯示自己的 chapters 與 Domains。
7. 新增筆記只寫入新考試的 notes table。
8. 刪除筆記不影響其他考試。
9. 未登入時仍依產品規則要求登入。

## 13. 可重複使用的 PDF 整理提示詞

未來可使用以下提示詞協助整理，但仍需人工核對技術內容：

```text
請把這份 <考試名稱> PDF 整理成 AWS Quiz Bank 學習卡牌 JSON。

規則：
1. 使用三層結構：chapter → topic → title → Domain/Description。
2. chapter 格式必須是「chapter數字: 章節名稱」，從 chapter1 開始且不可重複。
3. topic 是小章節，不加 01/02/03。
4. 只有流程、逐項要素或角色扮演目標具有順序時，title 才加 1./2./3.。
5. 一張卡只放一個主要觀念；可獨立出題的粗體重點要拆卡。
6. Title 優先使用 AWS 官方英文名稱或投影片粗體關鍵字。
7. Description 使用繁體中文，保留必要英文術語，包含定義、用途、差異、
   適用情境、限制及常見考試陷阱。
8. 先搜尋既有 JSON；相同觀念補強原卡，不建立重複卡。
9. Domain 必須使用 <考試名稱> 最新官方考試藍圖。
10. PDF 若有過度簡化或可能過時的敘述，以 AWS 官方文件確認，
    並在 Description 補充例外。
11. 不可增加 Domain、Description 以外的卡牌欄位。
12. 每個 chapter 必須且只能有一個「Shared Responsibility for <該章主題>」topic。
13. 沒有角色扮演時 Responsibility 放最後；有角色扮演時 Responsibility 放倒數第二、角色扮演放最後。
14. 正式角色扮演內容必須保留，不可因為相同知識已併入一般卡牌就刪除。
15. Description 長段落依完整句意拆分，段落間使用 `\n\n`；補充與常見考法標籤必須另起新段。
16. 最後檢查 JSON 語法、chapter 編號、重複 title 與內容歸類。

輸出前先提供：
- chapter 大綱
- 每個 chapter 的 topics
- 預計新增、更新、合併的卡牌清單

確認後再產生完整 JSON。
```

## 14. 發布前檢查清單

### 內容

- [ ] Chapter 對應課程大章節，而不是 PDF 頁碼。
- [ ] Topic 分類清楚，概念、類型、流程、責任與情境沒有混在一起。
- [ ] 一張卡只有一個主要觀念。
- [ ] 沒有重複卡牌。
- [ ] 每個 chapter 有且只有一個 `Shared Responsibility for ...` topic。
- [ ] 沒有角色扮演時 Responsibility 位於最後。
- [ ] 有角色扮演時 Responsibility 位於倒數第二、角色扮演位於最後。
- [ ] 課程原有的角色扮演 topic 與卡牌均有保留。
- [ ] 只有真正有順序的卡牌才編號。
- [ ] Title 對應官方術語或考試關鍵字。
- [ ] Description 有定義、用途、差異及考題線索。
- [ ] Description 沒有過長的大段文字，段落之間有一個空白行。
- [ ] `補充與常見考法`、`常見情境與考法`、`常見考法` 均另起新段。
- [ ] Domain 使用該考試官方藍圖。
- [ ] 數字、限制與服務功能已核對。

### JSON

- [ ] Chapter 符合 `chapter數字: 名稱`。
- [ ] Chapter 編號不重複。
- [ ] Topic、Title、Domain、Description 都不是空字串。
- [ ] 沒有未支援欄位。
- [ ] `jq empty` 成功。
- [ ] 來源檔與正式檔完全一致。

### Supabase

- [ ] 先執行 validate，再執行 sync。
- [ ] 檢查 inserted、updated、deactivated 是否符合預期。
- [ ] 再同步一次時全部 skipped。
- [ ] 重新分類沒有讓既有筆記消失。
- [ ] 新考試使用獨立 cards table 與 notes table。
- [ ] UI 切換考試後沒有混入其他考試資料。
