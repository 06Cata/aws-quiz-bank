"use client";

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";

const sampleOptions = [
  {
    key: "A",
    zh: "AWS Trusted Advisor",
    en: "Checks best practices but is not the EC2 vulnerability scanner."
  },
  {
    key: "B",
    zh: "Amazon Inspector",
    en: "Automated vulnerability management for EC2 workloads."
  },
  {
    key: "C",
    zh: "AWS Config",
    en: "Tracks resource configuration history."
  },
  {
    key: "D",
    zh: "Amazon GuardDuty",
    en: "Threat detection and continuous monitoring."
  }
];

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [isLoginPanelOpen, setIsLoginPanelOpen] = useState(false);
  const [authMessage, setAuthMessage] = useState("");

  useEffect(() => {
    const supabase = createClient();
    if (!supabase) {
      setAuthMessage("Vercel web 專案缺少 Supabase 前端環境變數");
      setIsCheckingSession(false);
      return;
    }

    supabase.auth
      .getUser()
      .then(({ data }) => {
        setUser(data.user);
      })
      .catch(() => {
        setAuthMessage("讀取登入狀態失敗");
      })
      .finally(() => {
        setIsCheckingSession(false);
      });

    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setAuthMessage("");
      setIsCheckingSession(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  async function signInWithGoogle() {
    setIsLoading(true);
    const supabase = createClient();
    if (!supabase) {
      setAuthMessage("尚未設定 NEXT_PUBLIC_SUPABASE_URL 或 NEXT_PUBLIC_SUPABASE_ANON_KEY");
      setIsLoading(false);
      setIsLoginPanelOpen(true);
      return;
    }

    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`
      }
    });

    if (error) {
      setAuthMessage(error.message);
      setIsLoading(false);
    }
  }

  async function signOut() {
    setIsLoading(true);
    const supabase = createClient();
    if (!supabase) {
      setAuthMessage("尚未設定 Supabase 前端環境變數");
      setIsLoading(false);
      return;
    }

    await supabase.auth.signOut();
    setUser(null);
    setIsLoading(false);
  }

  const gmail = user?.email ?? "";

  return (
    <main className="min-h-screen overflow-hidden px-6 py-8 text-zinc-100 md:px-12">
      <section className="mx-auto grid max-w-6xl gap-8 md:grid-cols-[0.95fr_1.05fr] md:items-center">
        <div className="space-y-8">
          <div className="inline-flex items-center gap-3 border border-zinc-700 bg-darkroom px-4 py-2 text-xs font-black tracking-[0.3em] text-flashYellow">
            <span className="h-2 w-2 rounded-full bg-acidGreen" />
            AWS 雲端從業人員
          </div>

          <div className="space-y-4">
            <h1 className="font-display text-5xl leading-none text-white md:text-7xl">
              AWS QUIZ
              <span className="block text-hotRed">BANK</span>
            </h1>
            <p className="max-w-xl text-lg leading-8 text-zinc-300">
              復古暗房感刷題介面。題目、選項、解析以中文優先，英文補充在後，答錯題目會累積錯誤次數。
            </p>
          </div>

          <button
            type="button"
            onClick={signInWithGoogle}
            disabled={isLoading}
            className="border-2 border-acidGreen bg-acidGreen px-7 py-4 font-display text-sm uppercase text-black shadow-[8px_8px_0_#ff3b30] transition hover:-translate-y-1 disabled:cursor-wait disabled:opacity-70"
          >
            {isLoading ? "正在連線..." : user ? "已登入 Google" : "使用 Google 登入"}
          </button>
        </div>

        <div className="film-frame bg-[#111] p-5">
          <div className="border border-zinc-800 bg-filmBlack p-5">
            <div className="mb-5 flex items-center justify-between border-b border-zinc-800 pb-4">
              <div>
                <p className="text-xs tracking-[0.28em] text-deepPink">第 003 題</p>
                <h2 className="mt-2 text-2xl font-black">安全性與合規</h2>
              </div>
              <span className="bg-flashYellow px-3 py-1 text-xs font-black text-black">單選</span>
            </div>

            <p className="text-xl font-bold leading-9 text-white">
              哪一項 AWS 服務可自動掃描 Amazon EC2 執行個體的軟體漏洞與非預期網路暴露？
            </p>
            <p className="mt-2 text-sm leading-6 text-zinc-400">
              Which AWS service automatically scans EC2 instances for software vulnerabilities and unintended network exposure?
            </p>

            <div className="mt-6 grid gap-3">
              {sampleOptions.map((option) => (
                <div
                  key={option.key}
                  className="border border-zinc-800 bg-[#181818] p-4 transition hover:border-acidGreen"
                >
                  <div className="flex gap-3">
                    <span className="grid h-8 w-8 shrink-0 place-items-center bg-hotRed font-black text-white">
                      {option.key}
                    </span>
                    <div>
                      <p className="font-bold">{option.zh}</p>
                      <p className="mt-1 text-sm text-zinc-400">{option.en}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 border-l-4 border-acidGreen bg-[#0d1a12] p-4">
              <p className="font-black text-acidGreen">正確答案：B. Amazon Inspector</p>
              <p className="mt-2 text-sm leading-6 text-zinc-300">
                選完後會立即顯示正確答案、各選項解析與社群討論。正式資料會從 Supabase questions 表讀取。
              </p>
            </div>
          </div>
        </div>
      </section>

      <aside className="fixed bottom-6 left-20 z-40 md:left-6">
        {isLoginPanelOpen ? (
          <div className="w-[min(380px,calc(100vw-112px))] border border-zinc-700 bg-[#090909]/95 p-4 shadow-[8px_8px_0_#ff3b30] backdrop-blur md:w-[360px]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-black tracking-[0.24em] text-flashYellow">登入狀態</p>
                <p className="mt-2 text-lg font-black text-white">
                  {isCheckingSession ? "檢查登入中" : user ? "已登入" : "尚未登入"}
                </p>
                <p className="mt-1 break-all text-sm text-zinc-300">
                  {isCheckingSession
                    ? "正在讀取 Supabase session"
                    : user
                      ? `目前 Gmail：${gmail}`
                      : authMessage || "目前沒有登入 Gmail 帳號"}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsLoginPanelOpen(false)}
                className="shrink-0 border border-zinc-700 px-3 py-2 text-sm font-bold text-zinc-300 transition hover:border-flashYellow hover:text-flashYellow"
                aria-label="收合登入狀態"
              >
                收合
              </button>
            </div>

            <div className="mt-4 flex gap-3">
              {user ? (
                <button
                  type="button"
                  onClick={signOut}
                  disabled={isLoading}
                  className="border border-zinc-600 px-4 py-2 text-sm font-bold text-zinc-100 transition hover:border-hotRed hover:text-hotRed disabled:cursor-wait disabled:opacity-70"
                >
                  登出
                </button>
              ) : (
                <button
                  type="button"
                  onClick={signInWithGoogle}
                  disabled={isLoading || isCheckingSession}
                  className="border border-acidGreen px-4 py-2 text-sm font-bold text-acidGreen transition hover:bg-acidGreen hover:text-black disabled:cursor-wait disabled:opacity-70"
                >
                  使用 Google 登入
                </button>
              )}
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setIsLoginPanelOpen(true)}
            className="flex items-center gap-3 border border-zinc-700 bg-[#090909]/95 px-4 py-3 text-left shadow-[6px_6px_0_#ff3b30] backdrop-blur transition hover:border-acidGreen"
            aria-expanded={isLoginPanelOpen}
            aria-label="打開登入狀態"
          >
            <span
              className={`h-3 w-3 rounded-full ${
                isCheckingSession ? "bg-flashYellow" : user ? "bg-acidGreen" : "bg-hotRed"
              }`}
            />
            <span>
              <span className="block text-xs font-black tracking-[0.2em] text-flashYellow">登入</span>
              <span className="block text-sm font-black text-white">
                {isCheckingSession ? "檢查中" : user ? "已登入" : "未登入"}
              </span>
            </span>
          </button>
        )}
      </aside>
    </main>
  );
}
