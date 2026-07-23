"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import {
  FLASHCARD_EXAMS,
  flashcardDomainKey,
  type Flashcard,
  type FlashcardDomainKey,
  type FlashcardExam,
  type FlashcardNote
} from "@/lib/flashcards";

type FlashcardWorkspaceProps = {
  mode: "study" | "notes";
};

export default function FlashcardWorkspace({ mode }: FlashcardWorkspaceProps) {
  const [selectedExam, setSelectedExam] = useState<FlashcardExam>("saa");
  const [hasRestoredExam, setHasRestoredExam] = useState(false);
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [notes, setNotes] = useState<FlashcardNote[]>([]);
  const [selectedChapter, setSelectedChapter] = useState("");
  const [selectedTopic, setSelectedTopic] = useState("all");
  const [selectedDomain, setSelectedDomain] = useState<FlashcardDomainKey>("all");
  const [cardIndex, setCardIndex] = useState(0);
  const [isRevealed, setIsRevealed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const environmentRequestId = useRef(0);
  const config = FLASHCARD_EXAMS[selectedExam];
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";

  useEffect(() => {
    const requestedExam = new URLSearchParams(window.location.search).get("exam");
    const storedExam = window.localStorage.getItem("aws-quiz-exam-type");
    const initialExam = requestedExam === "clf" || requestedExam === "saa"
      ? requestedExam
      : storedExam === "clf" || storedExam === "saa"
        ? storedExam
        : "saa";
    setSelectedExam(initialExam);
    window.localStorage.setItem("aws-quiz-exam-type", initialExam);
    setHasRestoredExam(true);
  }, []);

  useEffect(() => {
    if (!hasRestoredExam) return;
    const requestId = ++environmentRequestId.current;
    void loadEnvironment(selectedExam, requestId);
    return () => {
      if (environmentRequestId.current === requestId) {
        environmentRequestId.current += 1;
      }
    };
  }, [hasRestoredExam, selectedExam]);

  async function getAccessToken() {
    const supabase = createClient();
    if (!supabase) return null;
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }

  function isCurrentEnvironmentRequest(requestId?: number) {
    return requestId === undefined || environmentRequestId.current === requestId;
  }

  async function fetchNotes(exam: FlashcardExam, showLoginMessage: boolean, requestId?: number) {
    const accessToken = await getAccessToken();
    if (!isCurrentEnvironmentRequest(requestId)) return;
    if (!accessToken) {
      setNotes([]);
      if (showLoginMessage) setMessage("請先回首頁使用 Google 登入，才能讀取學習卡牌筆記。");
      return;
    }
    const response = await fetch(`${apiBaseUrl}${FLASHCARD_EXAMS[exam].apiPrefix}/flashcard-notes`, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${accessToken}` }
    });
    if (!response.ok) throw new Error("notes request failed");
    const data = (await response.json()) as { items?: FlashcardNote[] };
    if (!isCurrentEnvironmentRequest(requestId)) return;
    setNotes(data.items ?? []);
  }

  async function loadEnvironment(exam: FlashcardExam, requestId: number) {
    setIsLoading(true);
    setMessage("");
    setCards([]);
    setNotes([]);
    setSelectedChapter("");
    setSelectedTopic("all");
    setSelectedDomain("all");
    setCardIndex(0);
    setIsRevealed(false);
    if (!apiBaseUrl) {
      setMessage("尚未設定 NEXT_PUBLIC_API_BASE_URL，無法讀取學習卡牌。");
      setIsLoading(false);
      return;
    }
    const accessToken = await getAccessToken();
    if (!isCurrentEnvironmentRequest(requestId)) return;
    if (!accessToken) {
      setMessage("請先回首頁使用 Google 登入，才能使用學習卡牌功能。");
      setIsLoading(false);
      return;
    }
    try {
      const response = await fetch(`${apiBaseUrl}${FLASHCARD_EXAMS[exam].apiPrefix}/flashcards`, {
        cache: "no-store"
      });
      if (!response.ok) throw new Error("flashcards request failed");
      const data = (await response.json()) as { items?: Flashcard[] };
      if (!isCurrentEnvironmentRequest(requestId)) return;
      const nextCards = data.items ?? [];
      setCards(nextCards);
      setSelectedChapter(nextCards[0]?.chapter_key ?? "");
      await fetchNotes(exam, mode === "notes", requestId);
      if (!isCurrentEnvironmentRequest(requestId)) return;
      if (!nextCards.length) setMessage("這個考試目前沒有學習卡牌。");
    } catch {
      if (!isCurrentEnvironmentRequest(requestId)) return;
      setMessage("學習卡牌讀取失敗，請確認 API 與 Supabase 卡牌資料表。");
    } finally {
      if (isCurrentEnvironmentRequest(requestId)) {
        setIsLoading(false);
      }
    }
  }

  function switchExam(exam: FlashcardExam) {
    if (exam === selectedExam) return;
    window.localStorage.setItem("aws-quiz-exam-type", exam);
    const nextUrl = new URL(window.location.href);
    nextUrl.searchParams.set("exam", exam);
    window.history.replaceState({}, "", `${nextUrl.pathname}${nextUrl.search}`);
    setSelectedExam(exam);
  }

  const chapters = useMemo(() => {
    const seen = new Set<string>();
    return cards.filter((card) => {
      if (seen.has(card.chapter_key)) return false;
      seen.add(card.chapter_key);
      return true;
    }).map((card) => card.chapter_key);
  }, [cards]);

  const topics = useMemo(
    () => Array.from(new Set(cards.filter((card) => card.chapter_key === selectedChapter).map((card) => card.topic))),
    [cards, selectedChapter]
  );

  const studyCards = useMemo(
    () => cards.filter((card) =>
      card.chapter_key === selectedChapter && (selectedTopic === "all" || card.topic === selectedTopic)
    ),
    [cards, selectedChapter, selectedTopic]
  );

  const noteCards = useMemo(
    () => notes.filter((card) =>
      selectedDomain === "all" || flashcardDomainKey(card.exam_domain) === selectedDomain
    ),
    [notes, selectedDomain]
  );

  const noteByCardId = useMemo(() => new Map(notes.map((note) => [note.id, note])), [notes]);
  const currentCard = studyCards[cardIndex];
  const currentNote = currentCard ? noteByCardId.get(currentCard.id) : undefined;

  function changeChapter(chapter: string) {
    setSelectedChapter(chapter);
    setSelectedTopic("all");
    setCardIndex(0);
    setIsRevealed(false);
    setMessage("");
  }

  function changeTopic(topic: string) {
    setSelectedTopic(topic);
    setCardIndex(0);
    setIsRevealed(false);
  }

  function moveCard(direction: -1 | 1) {
    if (!studyCards.length) return;
    setCardIndex((index) => (index + direction + studyCards.length) % studyCards.length);
    setIsRevealed(false);
    setMessage("");
  }

  async function saveCurrentCard() {
    if (!currentCard || isSaving) return;
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setMessage("請先回首頁使用 Google 登入，才能儲存學習卡牌筆記。");
      return;
    }
    setIsSaving(true);
    setMessage("");
    try {
      const response = await fetch(`${apiBaseUrl}${config.apiPrefix}/flashcard-notes`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ flashcard_id: currentCard.id })
      });
      if (!response.ok) throw new Error("save note failed");
      await fetchNotes(selectedExam, false);
      setMessage("已存入學習卡牌筆記。");
    } catch {
      setMessage("學習卡牌筆記儲存失敗，請稍後再試。");
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteNote(noteId: string) {
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setMessage("請先登入才能刪除學習卡牌筆記。");
      return;
    }
    setIsSaving(true);
    try {
      const response = await fetch(`${apiBaseUrl}${config.apiPrefix}/flashcard-notes/${noteId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      if (!response.ok) throw new Error("delete note failed");
      setNotes((items) => items.filter((note) => note.note_id !== noteId));
      setMessage("已刪除學習卡牌筆記。");
    } catch {
      setMessage("學習卡牌筆記刪除失敗，請稍後再試。");
    } finally {
      setIsSaving(false);
    }
  }

  const domainOptions = [{ key: "all" as const, label: "全部" }, ...config.domains];

  return (
    <main className="min-h-screen px-5 py-8 text-zinc-100 md:px-12">
      <section className="mx-auto max-w-6xl">
        <div className="mb-7 grid grid-cols-1 border-2 border-zinc-700 bg-black sm:grid-cols-2">
          {(Object.entries(FLASHCARD_EXAMS) as [FlashcardExam, (typeof FLASHCARD_EXAMS)[FlashcardExam]][]).map(([exam, examConfig]) => (
            <button
              type="button"
              key={exam}
              onClick={() => switchExam(exam)}
              className={`min-h-14 px-4 py-3 text-sm font-black transition ${selectedExam === exam ? "bg-flashYellow text-black" : "text-zinc-400 hover:text-white"}`}
            >
              {examConfig.shortName}
            </button>
          ))}
        </div>

        <header className="mb-8 flex flex-col gap-5 border-b-2 border-zinc-800 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-black tracking-[0.28em] text-deepPink">{config.name}</p>
            <h1 className="mt-3 font-display text-4xl leading-none text-white md:text-6xl">
              {mode === "study" ? "學習卡牌" : "學習卡牌筆記"}
            </h1>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              {mode === "study"
                ? `由 ${selectedExam}_flashcards Supabase 表載入，共 ${cards.length} 張卡牌。`
                : `${config.shortName} 的收藏卡牌，與另一個考試環境完全分開。`}
            </p>
          </div>
          <nav className="flex flex-wrap gap-2" aria-label="學習卡牌導覽">
            <Link href="/" className="border border-zinc-700 px-4 py-2 text-sm font-black text-zinc-300 hover:border-white hover:text-white">回首頁</Link>
            <Link href={`${mode === "study" ? "/flashcard-notes" : "/flashcards"}?exam=${selectedExam}`} className="border border-flashYellow px-4 py-2 text-sm font-black text-flashYellow hover:bg-flashYellow hover:text-black">
              {mode === "study" ? `學習卡牌筆記 ${notes.length}` : "前往學習卡牌"}
            </Link>
          </nav>
        </header>

        {message ? <p className="mb-6 border-l-4 border-deepPink bg-[#170817] px-4 py-3 text-sm font-bold text-deepPink">{message}</p> : null}
        {isLoading ? <p className="border border-zinc-800 p-6 font-black text-flashYellow">讀取卡牌中...</p> : null}

        {!isLoading && mode === "study" ? (
          <div className="grid gap-8 lg:grid-cols-[300px_1fr]">
            <aside className="h-fit border-2 border-zinc-800 bg-black p-5">
              <label htmlFor="chapter-selector" className="text-xs font-black tracking-[0.2em] text-flashYellow">CHAPTER 選單</label>
              <select id="chapter-selector" value={selectedChapter} onChange={(event) => changeChapter(event.target.value)} className="mt-3 w-full border-2 border-zinc-700 bg-black px-3 py-3 font-black text-white outline-none focus:border-flashYellow">
                {chapters.map((chapter) => <option key={chapter} value={chapter}>{chapter}</option>)}
              </select>
              <p className="mb-3 mt-6 text-xs font-black tracking-[0.2em] text-zinc-500">章節主題</p>
              <div className="grid max-h-[50vh] gap-2 overflow-y-auto pr-1">
                <button type="button" onClick={() => changeTopic("all")} className={`border px-3 py-2 text-left text-sm font-bold ${selectedTopic === "all" ? "border-acidGreen bg-acidGreen text-black" : "border-zinc-800 text-zinc-300"}`}>全部主題</button>
                {topics.map((topic) => (
                  <button type="button" key={topic} onClick={() => changeTopic(topic)} className={`border px-3 py-2 text-left text-sm font-bold ${selectedTopic === topic ? "border-acidGreen bg-acidGreen text-black" : "border-zinc-800 text-zinc-300 hover:border-acidGreen"}`}>{topic}</button>
                ))}
              </div>
            </aside>

            <section>
              {currentCard ? (
                <>
                  <div className="mb-3 flex items-center justify-between gap-4 text-xs font-black text-zinc-500">
                    <span>{selectedChapter}</span><span>{cardIndex + 1} / {studyCards.length}</span>
                  </div>
                  <button type="button" onClick={() => setIsRevealed((value) => !value)} className="min-h-[430px] w-full border-2 border-flashYellow bg-[#101010] p-7 text-left shadow-[10px_10px_0_#ff3b30] transition hover:-translate-y-1 md:p-10" aria-expanded={isRevealed}>
                    <p className="text-xs font-black tracking-[0.12em] text-deepPink">{currentCard.exam_domain}</p>
                    <p className="mt-6 text-lg font-black leading-7 text-zinc-400">{currentCard.topic}</p>
                    <h2 className="mt-4 text-3xl font-black leading-tight text-white md:text-4xl">{currentCard.title}</h2>
                    {isRevealed ? (
                      <div className="mt-8 border-t border-zinc-700 pt-7">
                        <p className="mb-3 text-xs font-black tracking-[0.18em] text-flashYellow">解析</p>
                        <p className="whitespace-pre-line text-base font-medium leading-8 text-zinc-200 md:text-lg">{currentCard.description}</p>
                      </div>
                    ) : <p className="mt-10 text-sm font-black tracking-[0.18em] text-flashYellow">點擊卡牌查看解析</p>}
                  </button>
                  <div className="mt-7 grid grid-cols-3 gap-3">
                    <button type="button" onClick={() => moveCard(-1)} className="border-2 border-zinc-700 px-3 py-3 font-black hover:border-white">上一張</button>
                    <button type="button" onClick={saveCurrentCard} disabled={Boolean(currentNote) || isSaving} className={`border-2 px-3 py-3 font-black disabled:cursor-not-allowed ${currentNote ? "border-deepPink bg-deepPink text-white" : "border-deepPink text-deepPink hover:bg-deepPink hover:text-white"}`}>{currentNote ? "已存筆記" : isSaving ? "儲存中" : "存成筆記"}</button>
                    <button type="button" onClick={() => moveCard(1)} className="border-2 border-zinc-700 px-3 py-3 font-black hover:border-white">下一張</button>
                  </div>
                </>
              ) : <p className="border border-zinc-800 p-6 text-zinc-400">這個分類目前沒有卡牌。</p>}
            </section>
          </div>
        ) : null}

        {!isLoading && mode === "notes" ? (
          <section>
            <div className="mb-6 flex flex-wrap gap-2 border-b border-zinc-800 pb-6" aria-label="學習卡牌領域篩選">
              {domainOptions.map((domain) => {
                const count = domain.key === "all" ? notes.length : notes.filter((card) => flashcardDomainKey(card.exam_domain) === domain.key).length;
                const selected = selectedDomain === domain.key;
                return <button type="button" key={domain.key} onClick={() => setSelectedDomain(domain.key)} className={`border px-4 py-3 text-sm font-black ${selected ? "border-flashYellow bg-flashYellow text-black" : "border-zinc-700 bg-black text-zinc-300 hover:border-flashYellow"}`}>{domain.label} <span className={selected ? "text-black/60" : "text-zinc-500"}>{count}</span></button>;
              })}
            </div>
            {noteCards.length ? (
              <div className="grid gap-5 md:grid-cols-2">
                {noteCards.map((card) => (
                  <article key={card.note_id} className="border-2 border-zinc-800 bg-[#101010] p-5 shadow-[6px_6px_0_#ff3b30]">
                    <div className="flex items-start justify-between gap-4">
                      <p className="text-xs font-black leading-5 text-deepPink">{card.exam_domain}</p>
                      <button type="button" onClick={() => deleteNote(card.note_id)} disabled={isSaving} className="shrink-0 border border-zinc-700 px-2 py-1 text-xs font-black text-zinc-400 hover:border-hotRed hover:text-hotRed">刪除</button>
                    </div>
                    <p className="mt-3 text-xs font-bold text-zinc-600">{card.chapter_key}</p>
                    <p className="mt-4 text-base font-black leading-7 text-zinc-400">{card.topic}</p>
                    <h2 className="mt-2 text-xl font-black leading-8 text-white">{card.title}</h2>
                    <p className="mt-4 whitespace-pre-line border-l-4 border-flashYellow pl-4 text-sm leading-7 text-zinc-300">{card.description}</p>
                  </article>
                ))}
              </div>
            ) : <div className="border-l-4 border-zinc-700 bg-[#101010] p-6"><p className="font-black text-zinc-200">目前還沒有卡牌</p><p className="mt-2 text-sm leading-6 text-zinc-500">{notes.length ? "這個領域目前沒有收藏卡牌，請切換其他領域。" : "前往學習卡牌，按下「存成筆記」即可收藏。"}</p></div>}
          </section>
        ) : null}
      </section>
    </main>
  );
}
