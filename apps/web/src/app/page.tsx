"use client";

import { useEffect, useRef, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";

type LocalizedText = {
  zh?: string;
  en?: string;
};

type QuizQuestion = {
  id?: string;
  question_no?: number | null;
  exam_domain?: string | null;
  question_text: LocalizedText;
  options: Record<string, LocalizedText>;
  option_explanations?: Record<string, LocalizedText>;
  correct_options?: string[];
  answer_text?: LocalizedText | null;
  choice_type?: "single" | "multiple";
  discussion?: LocalizedText | null;
};

const sampleQuestion: QuizQuestion = {
  question_no: 3,
  exam_domain: "安全性與合規",
  question_text: {
    zh: "哪一項 AWS 服務可自動掃描 Amazon EC2 執行個體的軟體漏洞與非預期網路暴露？",
    en: "Which AWS service automatically scans EC2 instances for software vulnerabilities and unintended network exposure?"
  },
  options: {
    A: {
      zh: "AWS Trusted Advisor",
      en: "Checks best practices but is not the EC2 vulnerability scanner."
    },
    B: {
      zh: "Amazon Inspector",
      en: "Automated vulnerability management for EC2 workloads."
    },
    C: {
      zh: "AWS Config",
      en: "Tracks resource configuration history."
    },
    D: {
      zh: "Amazon GuardDuty",
      en: "Threat detection and continuous monitoring."
    }
  },
  option_explanations: {
    B: {
      zh: "Amazon Inspector 是用於自動化弱點管理，可掃描 EC2 工作負載。",
      en: "Amazon Inspector provides automated vulnerability management for EC2 workloads."
    }
  },
  correct_options: ["B"],
  choice_type: "single",
  discussion: {
    zh: "正式題目會從 Supabase questions 表讀取。",
    en: "Production questions are loaded from the Supabase questions table."
  }
};

function localizedText(value: LocalizedText | null | undefined, fallback = "") {
  return {
    zh: value?.zh?.trim() || fallback,
    en: value?.en?.trim() || ""
  };
}

function optionEntries(question: QuizQuestion) {
  return Object.entries(question.options ?? {}).sort(([left], [right]) => left.localeCompare(right));
}

function sortedOptionKeys(options: string[]) {
  return [...options].map((option) => option.trim().toUpperCase()).filter(Boolean).sort();
}

function sameOptions(left: string[], right: string[]) {
  const normalizedLeft = sortedOptionKeys(left);
  const normalizedRight = sortedOptionKeys(right);
  return normalizedLeft.length === normalizedRight.length
    && normalizedLeft.every((option, index) => option === normalizedRight[index]);
}

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [isLoginPanelOpen, setIsLoginPanelOpen] = useState(false);
  const [authMessage, setAuthMessage] = useState("");
  const [hasStartedQuiz, setHasStartedQuiz] = useState(false);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);
  const [quizMessage, setQuizMessage] = useState("");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [hasAnswered, setHasAnswered] = useState(false);
  const [isSavingAttempt, setIsSavingAttempt] = useState(false);
  const ensuredProfileUserIds = useRef<Set<string>>(new Set());
  const profileCheckInFlightUserId = useRef<string | null>(null);

  async function ensureMemberProfile(session: Session | null) {
    const userId = session?.user?.id;
    if (!session?.access_token || !userId) {
      return;
    }

    if (ensuredProfileUserIds.current.has(userId) || profileCheckInFlightUserId.current === userId) {
      return;
    }

    profileCheckInFlightUserId.current = userId;

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
    if (!apiBaseUrl) {
      setAuthMessage("已登入，但尚未設定 API 網址，無法確認會員資料");
      setIsLoginPanelOpen(true);
      profileCheckInFlightUserId.current = null;
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl}/api/profiles/me`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`
        }
      });

      if (!response.ok) {
        throw new Error("profile check failed");
      }

      const data = (await response.json()) as { created?: boolean };
      ensuredProfileUserIds.current.add(userId);
      if (data.created) {
        setAuthMessage("已自動建立會員資料");
        setIsLoginPanelOpen(true);
      }
    } catch {
      setAuthMessage("已登入，但會員資料確認失敗，請確認 FastAPI 已啟動");
      setIsLoginPanelOpen(true);
    } finally {
      profileCheckInFlightUserId.current = null;
    }
  }

  useEffect(() => {
    const supabase = createClient();
    if (!supabase) {
      setAuthMessage("Vercel web 專案缺少 Supabase 前端環境變數");
      setIsCheckingSession(false);
      return;
    }

    const code = new URLSearchParams(window.location.search).get("code");
    if (code) {
      supabase.auth
        .exchangeCodeForSession(code)
        .then(async ({ data, error }) => {
          if (error) {
            setAuthMessage(error.message);
            return;
          }

          const session = data.session ?? null;
          setUser(session?.user ?? null);
          await ensureMemberProfile(session);
          window.history.replaceState({}, document.title, window.location.pathname);
        })
        .catch(() => {
          setAuthMessage("Google 登入回傳處理失敗");
        })
        .finally(() => {
          setIsCheckingSession(false);
        });

      return;
    }

    supabase.auth
      .getSession()
      .then(async ({ data }) => {
        const session = data.session ?? null;
        setUser(session?.user ?? null);
        await ensureMemberProfile(session);
      })
      .catch(() => {
        setAuthMessage("讀取登入狀態失敗");
      })
      .finally(() => {
        setIsCheckingSession(false);
      });

    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setUser(session?.user ?? null);
      if (!session) {
        setAuthMessage("");
      }
      await ensureMemberProfile(session);
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

  async function loadQuestionSet(endpoint: string, emptyMessage: string, loadedMessage: string) {
    if (!user) {
      setQuizMessage("請先登入才能記錄您的答題狀態");
      setIsLoginPanelOpen(true);
      return;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
    if (!apiBaseUrl) {
      setQuizMessage("尚未設定 API 網址，無法讀取題庫");
      return;
    }

    const supabase = createClient();
    if (!supabase) {
      setQuizMessage("尚未設定 Supabase 前端環境變數，無法讀取題庫");
      return;
    }

    const { data } = await supabase.auth.getSession();
    const accessToken = data.session?.access_token;
    if (!accessToken) {
      setQuizMessage("請先登入才能記錄您的答題狀態");
      setIsLoginPanelOpen(true);
      return;
    }

    setIsLoadingQuestions(true);
    setQuizMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      });
      if (!response.ok) {
        throw new Error("questions request failed");
      }

      const data = (await response.json()) as { items?: QuizQuestion[] };
      const nextQuestions = data.items ?? [];

      if (nextQuestions.length === 0) {
        setQuizMessage(emptyMessage);
        return;
      }

      setQuestions(nextQuestions);
      setCurrentQuestionIndex(0);
      setSelectedOptions([]);
      setHasAnswered(false);
      setHasStartedQuiz(true);
      setQuizMessage(`${loadedMessage} ${nextQuestions.length} 題`);
    } catch {
      setQuizMessage("題庫讀取失敗，請確認 FastAPI 或 Vercel API 已啟動");
    } finally {
      setIsLoadingQuestions(false);
    }
  }

  async function startQuiz() {
    await loadQuestionSet(
      "/api/questions?limit=20",
      "目前題庫沒有可用題目，請先確認 Google Sheet 同步結果",
      "已載入"
    );
  }

  async function startWrongReview() {
    await loadQuestionSet(
      "/api/questions/wrong?limit=20",
      "目前沒有錯題紀錄，先完成幾題後再回來複習",
      "已載入錯題複習"
    );
  }

  function chooseOption(optionKey: string) {
    if (hasAnswered) {
      return;
    }

    if (currentQuestion?.choice_type === "multiple") {
      setSelectedOptions((options) =>
        options.includes(optionKey)
          ? options.filter((key) => key !== optionKey)
          : [...options, optionKey].sort()
      );
      return;
    }

    setSelectedOptions([optionKey]);
  }

  async function confirmAnswer() {
    if (selectedOptions.length === 0) {
      setQuizMessage("請先選擇答案，再按確定");
      return;
    }

    setQuizMessage("");
    setHasAnswered(true);

    if (!hasStartedQuiz || !currentQuestion?.id) {
      return;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
    if (!apiBaseUrl) {
      setQuizMessage("答案已顯示，但尚未設定 API 網址，無法寫入作答紀錄");
      return;
    }

    const supabase = createClient();
    if (!supabase) {
      setQuizMessage("答案已顯示，但尚未設定 Supabase，無法寫入作答紀錄");
      return;
    }

    const { data } = await supabase.auth.getSession();
    const accessToken = data.session?.access_token;
    if (!accessToken) {
      setQuizMessage("答案已顯示；登入後才會寫入錯題紀錄");
      return;
    }

    setIsSavingAttempt(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/attempts`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          selected_options: sortedOptionKeys(selectedOptions),
          is_correct: sameOptions(selectedOptions, correctOptions)
        })
      });

      if (!response.ok) {
        throw new Error("attempt request failed");
      }
    } catch {
      setQuizMessage("答案已顯示，但作答紀錄寫入失敗，請稍後再試");
    } finally {
      setIsSavingAttempt(false);
    }
  }

  function nextQuestion() {
    if (currentQuestionIndex + 1 >= questions.length) {
      setQuizMessage("已完成目前載入的題目");
      return;
    }

    setCurrentQuestionIndex((index) => index + 1);
    setSelectedOptions([]);
    setHasAnswered(false);
    setIsSavingAttempt(false);
  }

  const gmail = user?.email ?? "";
  const currentQuestion = hasStartedQuiz ? questions[currentQuestionIndex] : sampleQuestion;
  const questionText = localizedText(currentQuestion?.question_text);
  const discussion = localizedText(currentQuestion?.discussion);
  const correctOptions = currentQuestion?.correct_options ?? [];
  const currentOptions = currentQuestion ? optionEntries(currentQuestion) : [];
  const correctAnswerLabel = correctOptions.join(", ");
  const examDomain = currentQuestion?.exam_domain?.trim() || "尚未載入考試領域";

  return (
    <main className="min-h-screen overflow-hidden px-6 py-8 text-zinc-100 md:px-12">
      <section className="mx-auto grid max-w-6xl gap-8 md:grid-cols-[0.95fr_1.05fr] md:items-center">
        <div className="space-y-8">
          <div className="inline-flex items-center gap-3 border border-zinc-700 bg-darkroom px-4 py-2 text-xs font-black tracking-[0.3em] text-flashYellow">
            <span className="h-2 w-2 rounded-full bg-acidGreen" />
            AWS Cloud Practitioner
          </div>

          <div className="space-y-4">
            <h1 className="font-display text-5xl leading-none text-white md:text-7xl">
              AWS QUIZ
              <span className="block text-hotRed">BANK</span>
            </h1>
            <p className="max-w-xl text-lg leading-8 text-zinc-300">
              初次登入使用gmail帳號，系統會自動建立會員資料，並將答題紀錄寫入後端資料庫。若要複習錯題，請先完成幾題後再回來複習。
            </p>
          </div>

          <div className="flex flex-wrap gap-4">
            <button
              type="button"
              onClick={startQuiz}
              disabled={isLoadingQuestions}
              className="border-2 border-acidGreen bg-acidGreen px-7 py-4 font-display text-sm uppercase text-black shadow-[8px_8px_0_#ff3b30] transition hover:-translate-y-1 disabled:cursor-wait disabled:opacity-70"
            >
              {isLoadingQuestions ? "讀取題庫中..." : hasStartedQuiz ? "重新開始刷題" : "開始刷題"}
            </button>

            <button
              type="button"
              onClick={startWrongReview}
              disabled={isLoadingQuestions}
              className="border-2 border-flashYellow bg-black px-7 py-4 font-display text-sm uppercase text-flashYellow shadow-[8px_8px_0_#ff3b30] transition hover:-translate-y-1 disabled:cursor-wait disabled:opacity-70"
            >
              複習錯題
            </button>

            {!user ? (
              <button
                type="button"
                onClick={signInWithGoogle}
                disabled={isLoading}
                className="border-2 border-zinc-600 bg-black px-7 py-4 font-display text-sm uppercase text-zinc-100 transition hover:border-flashYellow hover:text-flashYellow disabled:cursor-wait disabled:opacity-70"
              >
                {isLoading ? "正在連線..." : "使用 Google 登入"}
              </button>
            ) : null}
          </div>

          {quizMessage ? (
            <p className="max-w-xl border-l-4 border-flashYellow bg-[#16120a] px-4 py-3 text-sm font-bold text-flashYellow">
              {quizMessage}
            </p>
          ) : null}
        </div>

        <div className="film-frame bg-[#111] p-5">
          <div className="border border-zinc-800 bg-filmBlack p-5">
            <div className="mb-5 flex items-center justify-between border-b border-zinc-800 pb-4">
              <div>
                <p className="text-xs tracking-[0.28em] text-deepPink">
                  {hasStartedQuiz ? `第 ${currentQuestionIndex + 1} / ${questions.length} 題` : "預覽題"}
                </p>
                <h2 className="mt-2 text-2xl font-black">{examDomain}</h2>
              </div>
              <span className="bg-flashYellow px-3 py-1 text-xs font-black text-black">
                {currentQuestion?.choice_type === "multiple" ? "複選" : "單選"}
              </span>
            </div>

            <p className="text-xl font-bold leading-9 text-white">
              {questionText.zh}
            </p>
            {questionText.en ? <p className="mt-2 text-sm leading-6 text-zinc-400">{questionText.en}</p> : null}

            <div className="mt-6 grid gap-3">
              {currentOptions.map(([optionKey, option]) => {
                const optionText = localizedText(option);
                const zhOptionText = optionText.zh || "（缺少繁體中文選項）";
                const isSelected = selectedOptions.includes(optionKey);
                const isCorrect = correctOptions.includes(optionKey);
                const answerStateClass = !hasAnswered
                  ? isSelected
                    ? "border-flashYellow bg-[#221c0b]"
                    : "border-zinc-800 bg-[#181818] hover:border-acidGreen"
                  : isCorrect
                    ? "border-acidGreen bg-[#0d1a12]"
                    : isSelected
                      ? "border-hotRed bg-[#1a0d0d]"
                      : "border-zinc-800 bg-[#181818] opacity-70";

                return (
                  <button
                    type="button"
                    key={optionKey}
                    onClick={() => chooseOption(optionKey)}
                    aria-label={`選項 ${optionKey}：${zhOptionText}`}
                    className={`border p-4 text-left transition ${answerStateClass}`}
                    disabled={hasAnswered}
                 >
                  <div className="flex gap-3">
                    <span className="grid h-8 w-8 shrink-0 place-items-center bg-hotRed font-black text-white">
                      {optionKey}
                    </span>
                    <div className="min-w-0">
                      <p className="text-lg font-black leading-7 text-zinc-100">{zhOptionText}</p>
                      {optionText.en ? (
                        <p className="mt-2 border-t border-white/10 pt-2 text-sm leading-6 text-zinc-500">
                          {optionText.en}
                        </p>
                      ) : null}
                    </div>
                  </div>
                  </button>
                );
              })}
            </div>

            {hasAnswered ? (
              <div className="mt-6 space-y-4">
                <div className="border-l-4 border-acidGreen bg-[#0d1a12] p-4">
                  <p className="font-black text-acidGreen">正確答案：{correctAnswerLabel}</p>
                  {correctOptions.length > 0 ? (
                    <p className="mt-2 text-sm leading-6 text-zinc-300">
                      你選擇：{selectedOptions.join(", ")}
                    </p>
                  ) : null}
                </div>

                {currentQuestion?.option_explanations && Object.keys(currentQuestion.option_explanations).length > 0 ? (
                  <div className="border border-zinc-800 bg-[#101010] p-4">
                    <p className="font-black text-flashYellow">各選項解析</p>
                    <div className="mt-3 grid gap-3">
                      {Object.entries(currentQuestion.option_explanations)
                        .sort(([left], [right]) => left.localeCompare(right))
                        .map(([key, explanation]) => {
                          const text = localizedText(explanation);
                          return (
                            <div key={key} className="border-l-2 border-zinc-700 pl-3">
                              <p className="text-sm font-black text-zinc-100">{key}. {text.zh}</p>
                              {text.en ? <p className="mt-1 text-xs leading-5 text-zinc-500">{text.en}</p> : null}
                            </div>
                          );
                        })}
                    </div>
                  </div>
                ) : null}

                {discussion.zh || discussion.en ? (
                  <div className="border border-zinc-800 bg-[#101010] p-4">
                    <p className="font-black text-deepPink">社群討論</p>
                    {discussion.zh ? <p className="mt-2 text-sm leading-6 text-zinc-300">{discussion.zh}</p> : null}
                    {discussion.en ? <p className="mt-1 text-xs leading-5 text-zinc-500">{discussion.en}</p> : null}
                  </div>
                ) : null}

                {hasStartedQuiz ? (
                  <button
                    type="button"
                    onClick={nextQuestion}
                    className="border border-flashYellow px-5 py-3 text-sm font-black text-flashYellow transition hover:bg-flashYellow hover:text-black"
                  >
                    {currentQuestionIndex + 1 >= questions.length ? "完成本輪" : "下一題"}
                  </button>
                ) : null}
              </div>
            ) : (
              <div className="mt-6 space-y-3">
                {hasStartedQuiz ? (
                  <button
                    type="button"
                    onClick={confirmAnswer}
                    disabled={selectedOptions.length === 0 || isSavingAttempt}
                    className="border-2 border-acidGreen bg-acidGreen px-6 py-3 font-display text-sm text-black shadow-[6px_6px_0_#ff3b30] transition hover:-translate-y-1 disabled:cursor-not-allowed disabled:border-zinc-700 disabled:bg-zinc-800 disabled:text-zinc-500 disabled:shadow-none"
                  >
                    {isSavingAttempt ? "紀錄中..." : "確定"}
                  </button>
                ) : null}
                <div className="border-l-4 border-zinc-700 bg-[#101010] p-4">
                  <p className="font-black text-zinc-200">
                    {hasStartedQuiz ? "選好答案後按「確定」才會顯示正確答案與解析" : "按左側「開始刷題」讀取正式題庫"}
                  </p>
                </div>
              </div>
            )}
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
                    : authMessage || (user ? `目前 Gmail：${gmail}` : "目前沒有登入 Gmail 帳號")}
                </p>
                {user && authMessage ? (
                  <p className="mt-1 break-all text-xs text-zinc-400">目前 Gmail：{gmail}</p>
                ) : null}
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
