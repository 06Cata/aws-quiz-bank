# AWS Quiz Bank

AWS Cloud Practitioner 與 AWS Solutions Architect Associate 刷題網站。前端使用 Next.js、React、TypeScript、Tailwind；後端 API 使用 FastAPI；資料庫與登入使用 Supabase。

## Project Structure

```text
aws-quiz-bank/
├── AWS_QUIZ_BUILD_GUIDE.md # 從 Supabase 建表、Google 登入到 Vercel 部署的實作指南
├── AWS_QUIZ_SITE_PLAN.md # 產品規劃、資料流、UI 規則與 Mermaid 架構圖
├── README.md # 專案入口說明
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
└── scripts/ # 同步與維運腳本預留資料夾
```

## Next Step

1. 確認 `apps/web/.env.local` 有 Supabase URL 與 anon key。
2. 安裝前端依賴：`npm install`
3. 啟動前端：`npm run dev:web`
4. 開啟 `http://localhost:3000` 測試 Google 登入。
5. 手動同步 CLF 題庫：`npm run sync:questions`
6. 手動同步 SAA 題庫：`npm run sync:questions:saa`

GitHub Actions 使用根目錄 `.github/workflows/sync-google-sheet.yml` 定期執行同一支同步程式。

## Docker

使用根目錄 `.env.local` 建置並啟動 production 容器：

```bash
docker compose --env-file .env.local up --build
```

開啟 `http://localhost:3000`，API 健康檢查是 `http://localhost:8000/health`。

執行一次 Google Sheet 題庫同步：

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
