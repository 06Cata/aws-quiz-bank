# AWS Quiz Bank

AWS Cloud Practitioner 與 AWS Solutions Architect Associate 刷題網站。前端使用 Next.js、React、TypeScript、Tailwind；後端 API 使用 FastAPI；資料庫與登入使用 Supabase。

## Project Structure

```text
aws-quiz-bank/
├── AWS_QUIZ_BUILD_GUIDE.md # 從 Supabase 建表、Google 登入到 Vercel 部署的實作指南
├── AWS_QUIZ_SITE_PLAN.md # 產品規劃、資料流、UI 規則與 Mermaid 架構圖
├── README.md # 專案入口說明
├── question_sources/ # PDF 原始來源、prompt_saa.md 與 prompt_clf.md
├── questions/ # 正式題庫，依 clf_ / saa_ 檔名前綴分流
├── package.json # monorepo npm scripts 與 workspace 設定
├── .env.example # 後端與同步工作需要的環境變數範例
├── .dockerignore # Docker build 排除本機依賴、快取與密鑰
├── compose.yaml # 一次啟動 Web、API 與題庫同步 job
├── apps/ # 前後端應用程式
│   ├── web/ # Next.js 前端
│   │   ├── Dockerfile # Next.js production standalone image
│   │   ├── package.json # 前端依賴與啟動指令
│   │   ├── next.config.ts # Next.js 設定
│   │   ├── postcss.config.mjs # Tailwind/PostCSS 設定
│   │   ├── tailwind.config.ts # Tailwind 掃描路徑與主題設定
│   │   ├── tsconfig.json # TypeScript 設定
│   │   ├── .env.local.example # 前端公開環境變數範例
│   │   └── src/ # 前端原始碼
│   │       ├── app/ # Next.js App Router
│   │       │   ├── auth/callback/route.ts # Supabase OAuth callback
│   │       │   ├── globals.css # Luxroom 風格全域樣式
│   │       │   ├── layout.tsx # 根 layout 與 metadata
│   │       │   └── page.tsx # 首頁與 Google 登入入口
│   │       └── lib/supabase/client.ts # 瀏覽器端 Supabase client
│   └── api/ # FastAPI 後端
│       ├── Dockerfile # FastAPI 與題庫同步共用 image
│       ├── requirements.txt # Python 依賴
│       └── app/ # API 原始碼
│           ├── main.py # FastAPI app 入口
│           ├── api/questions.py # 題目 API router
│           ├── api/saa.py # SAA 四大功能、作答與回合 API router
│           ├── core/config.py # 環境變數設定
│           └── services/supabase.py # CLF/SAA 白名單資料表與 Supabase REST 查詢服務
├── packages/ # 共用規格
│   └── shared/question-schema.md # 題目 JSON 欄位格式
``` 

## Next Step

以下流程適用於第一次在本機安裝、啟動及同步題庫。指令都從專案根目錄執行；建議使用 Python 3.12，並以虛擬環境隔離 API 依賴。

### 1. 取得最新程式碼

已經 clone 過專案時，先確認目前分支並下載遠端更新：

```bash
git status
git pull
```

`git pull` 顯示 `Already up to date.` 只代表目前分支與遠端一致，不代表 Python 或 npm 依賴已安裝，也不會把尚未 commit 的本機題庫上傳到 GitHub。

### 2. 安裝前端依賴

```bash
npm install
```

可先執行以下指令確認前端程式碼：

```bash
npm run lint:web
npm run build:web
```

### 3. 建立 Python 虛擬環境並安裝 API 依賴

macOS 或 Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r apps/api/requirements.txt
```

之後每次開啟新的終端機，都要先在專案根目錄啟用虛擬環境：

```bash
source .venv/bin/activate
```

若執行同步時出現 `ModuleNotFoundError: No module named 'pydantic_settings'` 或缺少 `supabase`，表示目前終端機使用的 Python 環境尚未安裝 `apps/api/requirements.txt`，或尚未啟用 `.venv`。可用以下指令確認實際使用的 Python：

```bash
which python
python --version
python -m pip --version
```

### 4. 設定環境變數

建立後端、同步工作及 Docker 共用的根目錄環境檔：

```bash
cp .env.example .env.local
```

編輯 `.env.local`，至少填入：

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
ALLOWED_ORIGINS=http://localhost:3000
WEB_API_BASE_URL=http://localhost:8000
WEB_APP_URL=http://localhost:3000
QUESTIONS_DIR=../../questions
QUIZ_EXAM=saa
```

再建立本機 Next.js 使用的環境檔：

```bash
cp apps/web/.env.local.example apps/web/.env.local
```

編輯 `apps/web/.env.local`：

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

`SUPABASE_SERVICE_ROLE_KEY` 只能放在根目錄 `.env.local`、部署平台的伺服器端環境變數或 GitHub Actions secrets，不可放入 `NEXT_PUBLIC_*` 變數，也不可 commit 到 Git。

Supabase 資料表、RLS policy 及 Google 登入尚未設定時，先依照 `AWS_QUIZ_BUILD_GUIDE.md` 完成 Supabase 專案設定。

### 5. 放置並驗證本機題庫

將正式 JSON 放入 `questions/`：

- CLF 檔名格式：`clf_Q起始題號-Q結束題號.json`，每檔最多 30 題。
- SAA 檔名格式：`saa_Q起始題號-Q結束題號.json`，每檔最多 15 題。
- 同一考試的題號必須從 Q1 開始連續，不可重複或缺號。

先執行本機驗證。這些指令不會連線或修改 Supabase：

```bash
npm run validate:questions:clf
npm run validate:questions:saa
```

成功輸出範例：

```text
Local JSON validation completed for clf: questions=30, latest=Q30
```

### 6. 將題庫增量同步至 Supabase

確認本機驗證通過且 `.env.local` 已設定後，再執行：

```bash
npm run sync:questions:clf
npm run sync:questions:saa
```

兩類題庫的寫入位置不同：

- CLF 寫入 Supabase `questions` table。
- SAA 寫入 Supabase `saa_questions` table。

同步器只新增 Supabase 最新題號之後的連續新題，不會更新或覆蓋已存在的題號。例如 Supabase 已有 Q1-Q30，再次同步本機 Q1-Q30 時會全部跳過；修改舊題內容後執行同步，也不會覆蓋資料庫舊內容。

如果 Supabase 的最新題號高於本機最後一題，或本機缺少下一個連續題號，同步器會停止。此時應先恢復完整本機題庫，不要直接跳號同步。

### 7. 啟動本機 API 與 Web

開啟兩個終端機。第一個終端機啟動 API：

```bash
source .venv/bin/activate
npm run dev:api
```

第二個終端機啟動 Web：

```bash
npm run dev:web
```

啟動後可檢查：

- Web：`http://localhost:3000`
- API 健康檢查：`http://localhost:8000/health`
- Google 登入：從 Web 首頁登入，確認能返回 `/auth/callback`。

### 8. 推送與自動同步

先確認不會提交 `.env.local`、金鑰或其他秘密，再提交程式碼與題庫：

```bash
git status
git add README.md questions/clf_Q1-Q30.json
git diff --cached
git commit -m "Update question bank"
git push
```

`git add` 請只列出本次確實要提交的檔案；不要在尚未確認 `git status` 時直接加入整個 `questions/`，以免意外提交其他題庫的刪除或無關修改。

GitHub repository 必須設定 `SUPABASE_URL` 與 `SUPABASE_SERVICE_ROLE_KEY` secrets。GitHub Actions 會在符合格式的 CLF 或 SAA 題庫檔案被 push 時執行同步，也可以手動執行；排程會在每日 16:00 UTC，也就是台灣時間隔日 00:00 執行。

若偏好 Docker，可跳過本機 Python 與 Node 啟動流程，改用下方的 Docker 指令；根目錄 `.env.local` 仍然必須設定完成。

## JSON 題庫增量同步

`questions` 是兩種考試共用的正式題庫來源。同步器依檔名前綴分流，檔案內的 `question_no` 必須完整、連續並與檔名一致：

| 檔名 | 每檔上限 | Supabase table |
| :--- | ---: | :--- |
| `clf_Q起始-Q結束.json` | 30 題 | `questions` |
| `saa_Q起始-Q結束.json` | 15 題 | `saa_questions` |

例如：

```text
questions/
├── clf_Q1-Q30.json
├── clf_Q31-Q60.json
├── saa_Q1-Q10.json
└── saa_Q11-Q25.json
```

執行同步時，程式只讀取指定考試前綴的 JSON，再查詢對應資料表最大的 `question_no`。只有比資料庫最大題號更大的連續題目會被新增；既有題目不會重新寫入。若資料庫最後是 Q20，但本機下一題從 Q22 開始，程式會停止並要求先補齊 Q21。若資料庫題號反而超過本機最後一題，也會停止。

```bash
npm run sync:questions:saa
npm run sync:questions:clf
```

只驗證檔名、schema、題號連續性並查看本機最後一題，不連線 Supabase：

```bash
npm run validate:questions
npm run validate:questions:saa
npm run validate:questions:clf
```

需要自訂題庫資料夾時可設定 `QUESTIONS_DIR`：

```bash
cd apps/api
QUESTIONS_DIR=/path/to/questions QUIZ_EXAM=saa python3 -m app.jobs.sync_local_questions
QUESTIONS_DIR=/path/to/questions QUIZ_EXAM=clf python3 -m app.jobs.sync_local_questions
```

## Docker

使用根目錄 `.env.local` 建置並啟動 production 容器：

```bash
docker compose --env-file .env.local up --build
```

開啟 `http://localhost:3000`，API 健康檢查是 `http://localhost:8000/health`。

執行一次本機 JSON 題庫增量同步：

```bash
docker compose --env-file .env.local --profile jobs run --rm sync-questions
```

同步 SAA 題庫：

```bash
QUIZ_EXAM=saa docker compose --env-file .env.local --profile jobs run --rm sync-questions
```

停止服務：

```bash
docker compose down
```
