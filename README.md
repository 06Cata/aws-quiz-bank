# AWS Quiz Bank

AWS Cloud Practitioner 與 AWS Solutions Architect Associate 刷題網站。前端使用 Next.js、React、TypeScript、Tailwind；後端 API 使用 FastAPI；資料庫與登入使用 Supabase。

## Project Structure

```text
aws-quiz-bank/
├── AWS_QUIZ_BUILD_GUIDE.md # 從 Supabase 建表、Google 登入到 Vercel 部署的實作指南
├── AWS_QUIZ_SITE_PLAN.md # 產品規劃、資料流、UI 規則與 Mermaid 架構圖
├── README.md # 專案入口說明
├── question_sources/ # PDF 原始來源與產生 JSON 的 prompt
├── questions/ # 正式題庫，只存放 Qx-Qy.json
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

1. 確認 `apps/web/.env.local` 有 Supabase URL 與 anon key。
2. 安裝前端依賴：`npm install`
3. 啟動前端：`npm run dev:web`
4. 開啟 `http://localhost:3000` 測試 Google 登入。
5. 將整理完成的題庫放入 `questions/Q1-Q10.json`、`questions/Q11-Q25.json` 等檔案，每個檔案最多 15 題。
6. 安裝 API 依賴：`python3 -m pip install -r apps/api/requirements.txt`
7. 手動增量同步 SAA 題庫：`npm run sync:questions:saa`

GitHub Actions 會在 `questions/Q*-Q*.json` 變更時執行同一支增量同步程式。

## JSON 題庫增量同步

`questions` 是正式題庫來源。每個檔案必須命名為 `Q起始題號-Q結束題號.json`，且檔案內的 `question_no` 必須完整、連續並與檔名一致，例如：

```text
questions/
├── Q1-Q10.json
├── Q11-Q25.json
└── Q26-Q40.json
```

執行同步時，程式會先驗證全部 JSON，再讀取 Supabase `saa_questions` 中最大的 `question_no`。只有比資料庫最大題號更大的連續題目會被新增；既有題目不會重新寫入。若資料庫最後是 Q20，但本機下一題從 Q22 開始，程式會停止並要求先補齊 Q21。若資料庫題號反而超過本機最後一題，也會停止，確保 `questions` 始終是完整的正式來源。

```bash
npm run sync:questions:saa
```

只驗證檔名、schema、題號連續性並查看本機最後一題，不連線 Supabase：

```bash
npm run validate:questions
```

需要自訂題庫資料夾時可設定 `QUESTIONS_DIR`：

```bash
cd apps/api
QUESTIONS_DIR=/path/to/questions QUIZ_EXAM=saa python3 -m app.jobs.sync_local_questions
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
