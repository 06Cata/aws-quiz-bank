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

type QuizMode = "practice" | "wrong" | "exam";
type ExamType = "clf" | "saa";

type ExamConfig = {
  name: string;
  shortName: string;
  apiPrefix: string;
  certification: string;
  mockQuestionCount: number;
  durationSeconds: number;
  resultNote: string;
};

type ExamResult = {
  correctCount: number;
  answeredCount: number;
  totalCount: number;
  accuracy: number;
  timedOut: boolean;
};

type ReviewNote = {
  id?: string;
  question_id?: string;
  option_key?: string;
  quiz_mode?: QuizMode;
  question_no?: number | null;
  exam_domain?: string | null;
  question_text?: LocalizedText;
  option_text?: LocalizedText;
  explanation_text?: LocalizedText;
  correct_options?: string[];
  updated_at?: string;
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

const EXAMS: Record<ExamType, ExamConfig> = {
  clf: {
    name: "AWS Cloud Practitioner",
    shortName: "Cloud Practitioner",
    apiPrefix: "/api",
    certification: "AWS Cloud Practitioner",
    mockQuestionCount: 65,
    durationSeconds: 90 * 60,
    resultNote: "AWS 基礎級考試滿分爲1000分，及格分數為 700 分，每題難易度與權重不同，建議在練習時，將目標穩定設定在 80% 以上的正確率"
  },
  saa: {
    name: "AWS Solutions Architect Associate",
    shortName: "Solutions Architect Associate",
    apiPrefix: "/api/saa",
    certification: "AWS Solutions Architect Associate",
    mockQuestionCount: 65,
    durationSeconds: 130 * 60,
    resultNote: "SAA 模擬考每題難易度與權重可能不同，建議在練習時，將目標穩定設定在 80% 以上的正確率"
  }
};

function formatExamTime(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

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

function createTimeoutSignal(timeoutMs = 8000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  return { signal: controller.signal, timeoutId };
}

function withTimeout<T>(promise: Promise<T>, timeoutMs = 5000): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => {
      window.setTimeout(() => reject(new Error("timeout")), timeoutMs);
    })
  ]);
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
  const [quizMode, setQuizMode] = useState<QuizMode>("practice");
  const [selectedExam, setSelectedExam] = useState<ExamType>("clf");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [examEndsAt, setExamEndsAt] = useState<number | null>(null);
  const [examSecondsRemaining, setExamSecondsRemaining] = useState(EXAMS.clf.durationSeconds);
  const [examCorrectCount, setExamCorrectCount] = useState(0);
  const [examAnsweredCount, setExamAnsweredCount] = useState(0);
  const [examResult, setExamResult] = useState<ExamResult | null>(null);
  const [isExamPaused, setIsExamPaused] = useState(false);
  const [isNotesOpen, setIsNotesOpen] = useState(false);
  const [isLoadingNotes, setIsLoadingNotes] = useState(false);
  const [isSavingNoteKey, setIsSavingNoteKey] = useState<string | null>(null);
  const [isDeletingNoteId, setIsDeletingNoteId] = useState<string | null>(null);
  const [notesMessage, setNotesMessage] = useState("");
  const [reviewNotes, setReviewNotes] = useState<ReviewNote[]>([]);
  const ensuredProfileUserIds = useRef<Set<string>>(new Set());
  const profileCheckInFlightUserId = useRef<string | null>(null);
  const isFinishingExam = useRef(false);
  const currentExam = EXAMS[selectedExam];

  useEffect(() => {
    const storedExam = window.localStorage.getItem("aws-quiz-exam-type");
    if (storedExam === "clf" || storedExam === "saa") {
      setSelectedExam(storedExam);
      setExamSecondsRemaining(EXAMS[storedExam].durationSeconds);
    }
  }, []);

  useEffect(() => {
    if (quizMode !== "exam" || !examEndsAt || examResult) {
      return;
    }

    const updateRemainingTime = () => {
      const remaining = Math.max(0, Math.ceil((examEndsAt - Date.now()) / 1000));
      setExamSecondsRemaining(remaining);
      if (remaining === 0) {
        void finalizeExam(true);
      }
    };

    updateRemainingTime();
    const intervalId = window.setInterval(updateRemainingTime, 1000);
    return () => window.clearInterval(intervalId);
  }, [examEndsAt, examResult, examCorrectCount, examAnsweredCount, quizMode, questions.length]);

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
      const { signal, timeoutId } = createTimeoutSignal();
      const response = await fetch(`${apiBaseUrl}/api/profiles/me`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`
        },
        signal
      });
      window.clearTimeout(timeoutId);

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
      withTimeout(supabase.auth.exchangeCodeForSession(code))
        .then(async ({ data, error }) => {
          if (error) {
            setAuthMessage(error.message);
            return;
          }

          const session = data.session ?? null;
          setUser(session?.user ?? null);
          void ensureMemberProfile(session);
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

    const sessionFallbackId = window.setTimeout(() => {
      setAuthMessage("登入狀態讀取逾時，請重新整理或重新登入");
      setIsCheckingSession(false);
    }, 5000);

    withTimeout(supabase.auth.getSession())
      .then(async ({ data }) => {
        window.clearTimeout(sessionFallbackId);
        const session = data.session ?? null;
        setUser(session?.user ?? null);
        void ensureMemberProfile(session);
      })
      .catch(() => {
        window.clearTimeout(sessionFallbackId);
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
      void ensureMemberProfile(session);
      setIsCheckingSession(false);
    });

    return () => {
      window.clearTimeout(sessionFallbackId);
      subscription.unsubscribe();
    };
  }, []);

  async function signInWithGoogle() {
    setIsLoading(true);
    setAuthMessage("");
    const supabase = createClient();
    if (!supabase) {
      setAuthMessage("尚未設定 NEXT_PUBLIC_SUPABASE_URL 或 NEXT_PUBLIC_SUPABASE_ANON_KEY");
      setIsLoading(false);
      setIsLoginPanelOpen(true);
      return;
    }

    try {
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
          skipBrowserRedirect: true
        }
      });

      if (error) {
        setAuthMessage(error.message);
        setIsLoginPanelOpen(true);
        setIsLoading(false);
        return;
      }

      if (!data.url) {
        setAuthMessage("Google 登入網址建立失敗，請確認 Supabase Google provider 設定");
        setIsLoginPanelOpen(true);
        setIsLoading(false);
        return;
      }

      window.location.assign(data.url);
    } catch {
      setAuthMessage("Google 登入啟動失敗，請重新整理後再試");
      setIsLoginPanelOpen(true);
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

  async function getAccessToken() {
    const supabase = createClient();
    if (!supabase) {
      return null;
    }

    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }

  async function switchExam(nextExam: ExamType) {
    if (nextExam === selectedExam) {
      return;
    }

    if (quizMode === "exam" && activeSessionId && !examResult) {
      const confirmed = window.confirm("目前有進行中的模擬考。切換題庫會提早結束本次模擬考，是否繼續？");
      if (!confirmed) {
        return;
      }
      try {
        await finishActiveSession();
      } catch {
        setQuizMessage("切換題庫成功，但原模擬考回合結束紀錄寫入失敗");
      }
    }

    const nextConfig = EXAMS[nextExam];
    window.localStorage.setItem("aws-quiz-exam-type", nextExam);
    setSelectedExam(nextExam);
    setQuestions([]);
    setCurrentQuestionIndex(0);
    setSelectedOptions([]);
    setHasAnswered(false);
    setHasStartedQuiz(false);
    setQuizMode("practice");
    setActiveSessionId(null);
    setIsNotesOpen(false);
    setReviewNotes([]);
    setQuizMessage("");
    setNotesMessage("");
    setExamEndsAt(null);
    setExamSecondsRemaining(nextConfig.durationSeconds);
    setExamCorrectCount(0);
    setExamAnsweredCount(0);
    setExamResult(null);
    setIsExamPaused(false);
    isFinishingExam.current = false;
  }

  function upsertNoteInState(note: ReviewNote) {
    setReviewNotes((notes) => {
      const noteQuestionId = note.question_id ?? "";
      const noteOptionKey = note.option_key ?? "";
      const remainingNotes = notes.filter((item) =>
        item.question_id !== noteQuestionId || item.option_key !== noteOptionKey
      );
      return [note, ...remainingNotes];
    });
  }

  async function loadReviewNotes() {
    if (!user) {
      setNotesMessage("請先登入才能讀取複習筆記");
      setIsLoginPanelOpen(true);
      return;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
    if (!apiBaseUrl) {
      setNotesMessage("尚未設定 API 網址，無法讀取複習筆記");
      return;
    }

    const accessToken = await getAccessToken();
    if (!accessToken) {
      setNotesMessage("請先登入才能讀取複習筆記");
      setIsLoginPanelOpen(true);
      return;
    }

    setIsLoadingNotes(true);
    setNotesMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}${currentExam.apiPrefix}/notes`, {
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      });

      if (!response.ok) {
        throw new Error("notes request failed");
      }

      const data = (await response.json()) as { items?: ReviewNote[] };
      setReviewNotes(data.items ?? []);
      setIsNotesOpen(true);
      setNotesMessage((data.items ?? []).length > 0 ? "" : "目前還沒有複習筆記");
    } catch {
      setNotesMessage("複習筆記讀取失敗，請確認 API 與 review_notes 資料表");
    } finally {
      setIsLoadingNotes(false);
    }
  }

  async function saveReviewNote(optionKey: string) {
    if (!user) {
      setNotesMessage("請先登入才能儲存複習筆記");
      setIsLoginPanelOpen(true);
      return;
    }

    if (!currentQuestion?.id) {
      setNotesMessage("預覽題不能存成筆記，請先開始刷題");
      return;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
    if (!apiBaseUrl) {
      setNotesMessage("尚未設定 API 網址，無法儲存複習筆記");
      return;
    }

    const accessToken = await getAccessToken();
    if (!accessToken) {
      setNotesMessage("請先登入才能儲存複習筆記");
      setIsLoginPanelOpen(true);
      return;
    }

    setIsSavingNoteKey(optionKey);
    setNotesMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}${currentExam.apiPrefix}/notes`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          option_key: optionKey,
          quiz_mode: quizMode
        })
      });

      if (!response.ok) {
        throw new Error("note request failed");
      }

      const data = (await response.json()) as { note?: ReviewNote };
      if (data.note) {
        upsertNoteInState(data.note);
      }
      setNotesMessage(`已將 ${optionKey} 選項解析存成筆記卡牌`);
    } catch {
      setNotesMessage("複習筆記儲存失敗，請確認 API 與 review_notes 資料表");
    } finally {
      setIsSavingNoteKey(null);
    }
  }

  async function deleteReviewNote(noteId: string | undefined) {
    if (!noteId) {
      setNotesMessage("缺少筆記 ID，無法刪除");
      return;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
    if (!apiBaseUrl) {
      setNotesMessage("尚未設定 API 網址，無法刪除複習筆記");
      return;
    }

    const accessToken = await getAccessToken();
    if (!accessToken) {
      setNotesMessage("請先登入才能刪除複習筆記");
      setIsLoginPanelOpen(true);
      return;
    }

    setIsDeletingNoteId(noteId);
    setNotesMessage("");

    try {
      const response = await fetch(`${apiBaseUrl}${currentExam.apiPrefix}/notes/${noteId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      });

      if (!response.ok) {
        throw new Error("delete note request failed");
      }

      setReviewNotes((notes) => notes.filter((note) => note.id !== noteId));
      setNotesMessage("已刪除複習筆記卡牌");
    } catch {
      setNotesMessage("複習筆記刪除失敗，請稍後再試");
    } finally {
      setIsDeletingNoteId(null);
    }
  }

  async function loadQuestionSet(
    endpoint: string,
    emptyMessage: string,
    loadedMessage: string,
    options: { mode: QuizMode; createSession?: boolean } = { mode: "practice" }
  ) {
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
        cache: "no-store",
        headers: {
          Authorization: `Bearer ${accessToken}`
        }
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as { items?: QuizQuestion[] };
      const nextQuestions = data.items ?? [];

      if (nextQuestions.length === 0) {
        setQuizMessage(emptyMessage);
        return;
      }

      let nextSessionId: string | null = null;
      if (options.createSession) {
        const sessionResponse = await fetch(`${apiBaseUrl}${currentExam.apiPrefix}/sessions`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            mode: options.mode,
            certification: currentExam.certification,
            question_count: nextQuestions.length
          })
        });

        if (!sessionResponse.ok) {
          throw new Error("session request failed");
        }

        const sessionData = (await sessionResponse.json()) as { session?: { id?: string } };
        nextSessionId = sessionData.session?.id ?? null;
      }

      setQuestions(nextQuestions);
      setCurrentQuestionIndex(0);
      setSelectedOptions([]);
      setHasAnswered(false);
      setHasStartedQuiz(true);
      setIsNotesOpen(false);
      setQuizMode(options.mode);
      setActiveSessionId(nextSessionId);
      setQuizMessage(`${loadedMessage} ${nextQuestions.length} 題`);
      isFinishingExam.current = false;
      setExamCorrectCount(0);
      setExamAnsweredCount(0);
      setExamResult(null);
      setIsExamPaused(false);
      if (options.mode === "exam") {
        setExamSecondsRemaining(currentExam.durationSeconds);
        setExamEndsAt(Date.now() + currentExam.durationSeconds * 1000);
      } else {
        setExamEndsAt(null);
      }
    } catch (error) {
      const reason = error instanceof Error ? error.message : "網路連線失敗";
      setQuizMessage(`題庫讀取失敗（${reason}），請稍後再試`);
    } finally {
      setIsLoadingQuestions(false);
    }
  }

  async function startQuiz() {
    await loadQuestionSet(
      `${currentExam.apiPrefix}/questions`,
      "目前題庫沒有可用題目，請先確認 Google Sheet 同步結果",
      "已載入",
      { mode: "practice" }
    );
  }

  async function startWrongReview() {
    await loadQuestionSet(
      `${currentExam.apiPrefix}/questions/wrong?limit=20`,
      "目前沒有錯題紀錄，先完成幾題後再回來複習",
      "已載入錯題複習",
      { mode: "wrong" }
    );
  }

  async function startMockExam() {
    await loadQuestionSet(
      `${currentExam.apiPrefix}/questions/exam?limit=${currentExam.mockQuestionCount}`,
      "目前題庫沒有可用題目，請先確認 Google Sheet 同步結果",
      "已建立模擬考回合",
      { mode: "exam", createSession: true }
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

    const isCorrectAnswer = sameOptions(selectedOptions, correctOptions);
    setQuizMessage("");
    setHasAnswered(true);

    if (quizMode === "exam") {
      setExamAnsweredCount((count) => count + 1);
      if (isCorrectAnswer) {
        setExamCorrectCount((count) => count + 1);
      }
    }

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
      const response = await fetch(`${apiBaseUrl}${currentExam.apiPrefix}/attempts`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          session_id: activeSessionId,
          question_id: currentQuestion.id,
          selected_options: sortedOptionKeys(selectedOptions),
          is_correct: isCorrectAnswer
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

  async function finishActiveSession() {
    if (!activeSessionId) {
      return;
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
    const supabase = createClient();
    if (!apiBaseUrl || !supabase) {
      return;
    }

    const { data } = await supabase.auth.getSession();
    const accessToken = data.session?.access_token;
    if (!accessToken) {
      return;
    }

    const response = await fetch(`${apiBaseUrl}${currentExam.apiPrefix}/sessions/${activeSessionId}/finish`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    });

    if (!response.ok) {
      throw new Error("finish session failed");
    }
  }

  async function finalizeExam(timedOut = false) {
    if (isFinishingExam.current || examResult) {
      return;
    }

    isFinishingExam.current = true;
    setExamEndsAt(null);
    setExamSecondsRemaining(0);
    setIsExamPaused(false);

    const totalCount = questions.length;
    const accuracy = totalCount > 0 ? Math.round((examCorrectCount / totalCount) * 1000) / 10 : 0;
    setExamResult({
      correctCount: examCorrectCount,
      answeredCount: examAnsweredCount,
      totalCount,
      accuracy,
      timedOut
    });

    try {
      await finishActiveSession();
      setActiveSessionId(null);
      setQuizMessage(timedOut ? "模擬考時間到，系統已自動交卷" : "模擬考已完成");
    } catch {
      setQuizMessage("模擬考已結束，但回合結束紀錄寫入失敗，請稍後再試");
    }
  }

  function toggleExamPause() {
    if (examResult) {
      return;
    }

    if (isExamPaused) {
      setExamEndsAt(Date.now() + examSecondsRemaining * 1000);
      setIsExamPaused(false);
      return;
    }

    const remaining = examEndsAt
      ? Math.max(0, Math.ceil((examEndsAt - Date.now()) / 1000))
      : examSecondsRemaining;
    setExamSecondsRemaining(remaining);
    setExamEndsAt(null);
    setIsExamPaused(true);
  }

  function finishExamEarly() {
    const confirmed = window.confirm("確定要提早結束模擬考嗎？未作答題目仍會計入正確率分母。");
    if (confirmed) {
      void finalizeExam(false);
    }
  }

  async function nextQuestion() {
    if (currentQuestionIndex + 1 >= questions.length) {
      if (quizMode === "exam") {
        await finalizeExam(false);
        return;
      }
      try {
        await finishActiveSession();
        setActiveSessionId(null);
        setQuizMessage("已完成目前載入的題目");
      } catch {
        setQuizMessage("題目已完成，但回合結束紀錄寫入失敗，請稍後再試");
      }
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
      {quizMode === "exam" && hasStartedQuiz && !examResult ? (
        <div
          className="fixed left-1/2 top-3 z-50 flex -translate-x-1/2 items-center gap-3 border-2 border-deepPink bg-black px-3 py-2 shadow-[5px_5px_0_#ff3b30] md:left-8 md:top-6 md:translate-x-0"
          role="timer"
          aria-label={`模擬考剩餘時間 ${formatExamTime(examSecondsRemaining)}`}
        >
          <div className="shrink-0">
            <p className="text-[9px] font-black tracking-[0.14em] text-zinc-400">模擬考剩餘時間</p>
            <p className="mt-1 font-display text-xl leading-none text-deepPink">
              {formatExamTime(examSecondsRemaining)}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={toggleExamPause}
              className="border border-flashYellow px-2 py-1 text-xs font-black text-flashYellow transition hover:bg-flashYellow hover:text-black"
            >
              {isExamPaused ? "繼續" : "暫停"}
            </button>
            <button
              type="button"
              onClick={finishExamEarly}
              className="border border-hotRed px-2 py-1 text-xs font-black text-hotRed transition hover:bg-hotRed hover:text-black"
            >
              提早結束
            </button>
          </div>
        </div>
      ) : null}

      <section className="mx-auto grid max-w-6xl gap-8 md:grid-cols-[0.95fr_1.05fr] md:items-center">
        <div className="space-y-8">
          <div className="max-w-lg">
            <label htmlFor="exam-selector" className="mb-2 block text-xs font-black tracking-[0.2em] text-zinc-500 md:hidden">
              目前題庫
            </label>
            <select
              id="exam-selector"
              value={selectedExam}
              onChange={(event) => void switchExam(event.target.value as ExamType)}
              className="w-full border-2 border-zinc-700 bg-black px-4 py-3 text-sm font-black text-white outline-none focus:border-flashYellow md:hidden"
            >
              <option value="clf">AWS Cloud Practitioner</option>
              <option value="saa">AWS Solutions Architect Associate</option>
            </select>

            <div className="hidden grid-cols-2 border-2 border-zinc-700 bg-black md:grid">
              {(Object.entries(EXAMS) as [ExamType, ExamConfig][]).map(([examKey, exam]) => (
                <button
                  type="button"
                  key={examKey}
                  onClick={() => void switchExam(examKey)}
                  aria-pressed={selectedExam === examKey}
                  className={`min-h-14 px-4 py-3 text-sm font-black transition ${
                    selectedExam === examKey
                      ? "bg-flashYellow text-black"
                      : "text-zinc-400 hover:text-white"
                  }`}
                >
                  {exam.shortName}
                </button>
              ))}
            </div>
          </div>

          <div className="inline-flex items-center gap-3 border border-zinc-700 bg-darkroom px-4 py-2 text-xs font-black tracking-[0.3em] text-flashYellow">
            <span className="h-2 w-2 rounded-full bg-acidGreen" />
            {currentExam.name}
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

          <div className="grid max-w-lg gap-5 sm:grid-cols-2">
            <div className="space-y-3">
              <button
                type="button"
                onClick={startQuiz}
                disabled={isLoadingQuestions}
                className="w-full border-2 border-acidGreen bg-acidGreen px-7 py-4 font-display text-sm uppercase text-black shadow-[8px_8px_0_#ff3b30] transition hover:-translate-y-1 disabled:cursor-wait disabled:opacity-70"
              >
                {isLoadingQuestions ? "讀取題庫中..." : hasStartedQuiz ? "重新開始刷題" : "開始刷題"}
              </button>

              <button
                type="button"
                onClick={startMockExam}
                disabled={isLoadingQuestions}
                className="w-full border-2 border-deepPink bg-black px-7 py-4 text-center font-display text-sm uppercase text-deepPink shadow-[8px_8px_0_#ff3b30] transition hover:-translate-y-1 disabled:cursor-wait disabled:opacity-70"
              >
                模擬考模式
              </button>
            </div>

            <div className="space-y-3">
              <button
                type="button"
                onClick={startWrongReview}
                disabled={isLoadingQuestions}
                className="w-full border-2 border-flashYellow bg-black px-7 py-4 font-display text-sm uppercase text-flashYellow shadow-[8px_8px_0_#ff3b30] transition hover:-translate-y-1 disabled:cursor-wait disabled:opacity-70"
              >
                複習錯題
              </button>

              <button
                type="button"
                onClick={isNotesOpen ? () => setIsNotesOpen(false) : loadReviewNotes}
                disabled={isLoadingNotes}
                className="w-full border-2 border-hotRed bg-black px-7 py-4 text-center font-display text-sm uppercase text-zinc-100 shadow-[8px_8px_0_#ff3b30] transition hover:-translate-y-1 disabled:cursor-wait disabled:opacity-70"
              >
                複習筆記
              </button>
            </div>

            {!user ? (
              <button
                type="button"
                onClick={signInWithGoogle}
                disabled={isLoading}
                className="border-2 border-zinc-600 bg-black px-7 py-4 font-display text-sm uppercase text-zinc-100 transition hover:border-flashYellow hover:text-flashYellow disabled:cursor-wait disabled:opacity-70 sm:col-span-2"
              >
                {isLoading ? "正在連線..." : "使用 Google 登入"}
              </button>
            ) : null}
          </div>

          {user ? (
            <div className="max-w-lg border border-zinc-700 bg-[#090909] p-3 md:hidden">
              <button
                type="button"
                onClick={() => setIsLoginPanelOpen((open) => !open)}
                className="flex w-full items-center justify-between gap-3 text-left"
                aria-expanded={isLoginPanelOpen}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-acidGreen" />
                  <span className="truncate text-sm font-black text-white">已登入 {gmail}</span>
                </span>
                <span className="shrink-0 text-xs font-bold text-zinc-400">
                  {isLoginPanelOpen ? "收合" : "帳號"}
                </span>
              </button>

              {isLoginPanelOpen ? (
                <div className="mt-3 border-t border-zinc-800 pt-3">
                  {authMessage ? <p className="mb-3 text-xs text-zinc-400">{authMessage}</p> : null}
                  <button
                    type="button"
                    onClick={signOut}
                    disabled={isLoading}
                    className="border border-zinc-600 px-3 py-2 text-xs font-bold text-zinc-100 disabled:cursor-wait disabled:opacity-70"
                  >
                    登出
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}

          {quizMessage ? (
            <p className="max-w-xl border-l-4 border-flashYellow bg-[#16120a] px-4 py-3 text-sm font-bold text-flashYellow">
              {quizMessage}
            </p>
          ) : null}

          {notesMessage ? (
            <p className="max-w-xl border-l-4 border-deepPink bg-[#170817] px-4 py-3 text-sm font-bold text-deepPink">
              {notesMessage}
            </p>
          ) : null}

        </div>

        <div className="film-frame bg-[#111] p-5">
          {isNotesOpen ? (
            <div className="border border-zinc-800 bg-filmBlack p-5">
              <div className="mb-5 flex items-center justify-between gap-4 border-b border-zinc-800 pb-4">
                <div>
                  <p className="text-xs tracking-[0.28em] text-deepPink">複習資料</p>
                  <h2 className="mt-2 text-2xl font-black text-flashYellow">複習筆記卡牌</h2>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={loadReviewNotes}
                    disabled={isLoadingNotes}
                    className="border border-zinc-700 px-3 py-2 text-xs font-black text-zinc-300 transition hover:border-flashYellow hover:text-flashYellow disabled:cursor-wait disabled:opacity-60"
                  >
                    重新整理
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsNotesOpen(false)}
                    className="border border-zinc-700 px-3 py-2 text-xs font-black text-zinc-300 transition hover:border-hotRed hover:text-hotRed"
                  >
                    返回題目
                  </button>
                </div>
              </div>

              {reviewNotes.length > 0 ? (
                <div className="grid max-h-[70vh] gap-4 overflow-y-auto pr-2">
                  {reviewNotes.map((note) => {
                    const noteQuestionText = localizedText(note.question_text);
                    const noteOptionText = localizedText(note.option_text);
                    const noteExplanationText = localizedText(note.explanation_text);
                    const noteKey = `${note.question_id}-${note.option_key}`;

                    return (
                      <article key={noteKey} className="border border-zinc-800 bg-[#121212] p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-xs font-black tracking-[0.18em] text-deepPink">
                            {note.exam_domain || "未分類"}
                          </p>
                          <div className="flex shrink-0 items-center gap-2">
                            <span className="grid h-8 w-8 place-items-center bg-hotRed text-sm font-black text-white">
                              {note.option_key}
                            </span>
                            <button
                              type="button"
                              onClick={() => deleteReviewNote(note.id)}
                              disabled={isDeletingNoteId === note.id}
                              className="border border-zinc-700 px-2 py-1 text-xs font-black text-zinc-400 transition hover:border-hotRed hover:text-hotRed disabled:cursor-wait disabled:opacity-60"
                            >
                              {isDeletingNoteId === note.id ? "刪除中" : "刪除"}
                            </button>
                          </div>
                        </div>
                        <p className="mt-4 text-base font-black leading-7 text-white">
                          {noteQuestionText.zh || noteQuestionText.en || "缺少題目文字"}
                        </p>
                        <p className="mt-4 border-l-4 border-flashYellow pl-3 text-lg font-black leading-7 text-zinc-100">
                          {noteOptionText.zh || noteOptionText.en || "缺少選項文字"}
                        </p>
                        {noteExplanationText.zh || noteExplanationText.en ? (
                          <p className="mt-3 text-sm leading-7 text-zinc-400">
                            {noteExplanationText.zh || noteExplanationText.en}
                          </p>
                        ) : null}
                      </article>
                    );
                  })}
                </div>
              ) : (
                <div className="border-l-4 border-zinc-700 bg-[#101010] p-4">
                  <p className="font-black text-zinc-200">目前還沒有卡牌</p>
                  <p className="mt-2 text-sm leading-6 text-zinc-500">
                    回到題目，答題後在各選項解析旁按「存成筆記」。
                  </p>
                </div>
              )}
            </div>
          ) : (
          <div className="border border-zinc-800 bg-filmBlack p-5">
            <div className="mb-5 flex items-center justify-between gap-4 border-b border-zinc-800 pb-4">
              <div>
                <p className="text-xs tracking-[0.28em] text-deepPink">
                  {hasStartedQuiz ? `第 ${currentQuestionIndex + 1} / ${questions.length} 題` : "預覽題"}
                </p>
                <h2 className="mt-2 text-2xl font-black">{examDomain}</h2>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-2">
                <span className="bg-flashYellow px-3 py-1 text-xs font-black text-black">
                  {currentQuestion?.choice_type === "multiple" ? "複選" : "單選"}
                </span>
              </div>
            </div>

            {examResult ? (
              <div className="border-l-4 border-acidGreen bg-[#0d1a12] p-5">
                <p className="text-xs font-black tracking-[0.22em] text-acidGreen">
                  {examResult.timedOut ? "時間到，自動交卷" : "模擬考完成"}
                </p>
                <p className="mt-3 font-display text-4xl text-white">正確率 {examResult.accuracy}%</p>
                <p className="mt-3 text-sm font-bold text-zinc-300">
                  答對 {examResult.correctCount} 題／共 {examResult.totalCount} 題
                  {examResult.answeredCount < examResult.totalCount
                    ? `，已作答 ${examResult.answeredCount} 題`
                    : ""}
                </p>
                <p className="mt-5 border-t border-white/10 pt-4 text-xs leading-6 text-zinc-400">
                  {currentExam.resultNote}
                </p>
              </div>
            ) : (
            <>
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
                    : "border-zinc-800 bg-[#181818]"
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
                              <div className="flex items-start justify-between gap-3">
                                <p className="text-sm font-black text-zinc-100">{key}. {text.zh}</p>
                                {hasStartedQuiz && currentQuestion?.id ? (
                                  <button
                                    type="button"
                                    onClick={() => saveReviewNote(key)}
                                    disabled={isSavingNoteKey === key}
                                    className="shrink-0 border border-flashYellow px-2 py-1 text-xs font-black text-flashYellow transition hover:bg-flashYellow hover:text-black disabled:cursor-wait disabled:opacity-60"
                                  >
                                    {isSavingNoteKey === key ? "儲存中" : "存成筆記"}
                                  </button>
                                ) : null}
                              </div>
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
            </>
            )}
          </div>
          )}
        </div>
      </section>

      <footer className="mx-auto mt-10 max-w-6xl pb-28 text-right text-xs text-zinc-500 md:pb-6">
        <a
          href="mailto:catalinakuowork@gmail.com"
          aria-label="寄信給開發者 catalinakuowork@gmail.com"
          className="font-bold underline decoration-zinc-700 underline-offset-4 transition hover:text-flashYellow hover:decoration-flashYellow"
        >
          寄信給開發者
        </a>
        <span className="ml-2">catalinakuowork@gmail.com</span>
      </footer>

      <aside className="fixed bottom-6 left-6 z-40 hidden md:block">
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
                  disabled={isLoading}
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
            onClick={() => {
              if (user) {
                setIsLoginPanelOpen(true);
                return;
              }
              void signInWithGoogle();
            }}
            disabled={isLoading}
            className="flex items-center gap-2 border border-zinc-700 bg-[#090909]/95 px-3 py-2 text-left shadow-[4px_4px_0_#ff3b30] backdrop-blur transition hover:border-zinc-500"
            aria-expanded={isLoginPanelOpen}
            aria-label={user ? "打開登入狀態" : "使用 Google 登入"}
          >
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                isCheckingSession ? "bg-flashYellow" : user ? "bg-acidGreen" : "bg-hotRed"
              }`}
            />
            <span>
              <span className="block text-xs font-black tracking-[0.16em] text-flashYellow">登入</span>
            </span>
          </button>
        )}
      </aside>
    </main>
  );
}
