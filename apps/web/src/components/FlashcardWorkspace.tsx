"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  CLF_FLASHCARDS,
  CLF_FLASHCARD_DOMAINS,
  FLASHCARD_CONTENTS,
  flashcardDomainKey,
  readSavedFlashcardIds,
  writeSavedFlashcardIds,
  type FlashcardDomainKey
} from "@/lib/flashcards";

type FlashcardWorkspaceProps = {
  mode: "study" | "notes";
};

export default function FlashcardWorkspace({ mode }: FlashcardWorkspaceProps) {
  const [selectedContent, setSelectedContent] = useState(FLASHCARD_CONTENTS[0] ?? "");
  const [selectedTopic, setSelectedTopic] = useState("all");
  const [selectedDomain, setSelectedDomain] = useState<FlashcardDomainKey>("all");
  const [cardIndex, setCardIndex] = useState(0);
  const [isRevealed, setIsRevealed] = useState(false);
  const [savedIds, setSavedIds] = useState<string[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setSavedIds(readSavedFlashcardIds());
  }, []);

  const topics = useMemo(
    () => Array.from(new Set(
      CLF_FLASHCARDS.filter((card) => card.content === selectedContent).map((card) => card.topic)
    )),
    [selectedContent]
  );

  const studyCards = useMemo(
    () => CLF_FLASHCARDS.filter((card) =>
      card.content === selectedContent && (selectedTopic === "all" || card.topic === selectedTopic)
    ),
    [selectedContent, selectedTopic]
  );

  const noteCards = useMemo(() => {
    const saved = new Set(savedIds);
    return CLF_FLASHCARDS.filter((card) =>
      saved.has(card.id)
      && (selectedDomain === "all" || flashcardDomainKey(card.Domain) === selectedDomain)
    );
  }, [savedIds, selectedDomain]);

  const currentCard = studyCards[cardIndex];
  const currentCardIsSaved = currentCard ? savedIds.includes(currentCard.id) : false;

  function changeContent(content: string) {
    setSelectedContent(content);
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

  function toggleSaved(cardId: string) {
    const isSaved = savedIds.includes(cardId);
    const nextSavedIds = isSaved
      ? savedIds.filter((id) => id !== cardId)
      : [...savedIds, cardId];
    setSavedIds(nextSavedIds);
    writeSavedFlashcardIds(nextSavedIds);
    setMessage(isSaved ? "已從學習卡牌筆記移除" : "已存入學習卡牌筆記");
  }

  const domainOptions = [{ key: "all" as const, label: "全部" }, ...CLF_FLASHCARD_DOMAINS];

  return (
    <main className="min-h-screen px-5 py-8 text-zinc-100 md:px-12">
      <section className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-5 border-b-2 border-zinc-800 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-black tracking-[0.28em] text-deepPink">AWS CLOUD PRACTITIONER</p>
            <h1 className="mt-3 font-display text-4xl leading-none text-white md:text-6xl">
              {mode === "study" ? "學習卡牌" : "學習卡牌筆記"}
            </h1>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              {mode === "study"
                ? `由 clf_flashcards.json 載入，共 ${CLF_FLASHCARDS.length} 張卡牌。`
                : "收藏的學習卡牌會保存在這台裝置，可依四大考試領域切換。"}
            </p>
          </div>
          <nav className="flex flex-wrap gap-2" aria-label="學習卡牌導覽">
            <Link href="/" className="border border-zinc-700 px-4 py-2 text-sm font-black text-zinc-300 hover:border-white hover:text-white">
              回首頁
            </Link>
            <Link
              href={mode === "study" ? "/flashcard-notes" : "/flashcards"}
              className="border border-flashYellow px-4 py-2 text-sm font-black text-flashYellow hover:bg-flashYellow hover:text-black"
            >
              {mode === "study" ? `學習卡牌筆記 ${savedIds.length}` : "前往學習卡牌"}
            </Link>
          </nav>
        </header>

        {mode === "study" ? (
          <div className="grid gap-8 lg:grid-cols-[300px_1fr]">
            <aside className="h-fit border-2 border-zinc-800 bg-black p-5">
              <label htmlFor="content-selector" className="text-xs font-black tracking-[0.2em] text-flashYellow">
                CONTENT 選單
              </label>
              <select
                id="content-selector"
                value={selectedContent}
                onChange={(event) => changeContent(event.target.value)}
                className="mt-3 w-full border-2 border-zinc-700 bg-black px-3 py-3 font-black text-white outline-none focus:border-flashYellow"
              >
                {FLASHCARD_CONTENTS.map((content) => (
                  <option key={content} value={content}>{content}</option>
                ))}
              </select>

              <p className="mb-3 mt-6 text-xs font-black tracking-[0.2em] text-zinc-500">主題</p>
              <div className="grid max-h-[50vh] gap-2 overflow-y-auto pr-1">
                <button
                  type="button"
                  onClick={() => changeTopic("all")}
                  className={`border px-3 py-2 text-left text-sm font-bold ${selectedTopic === "all" ? "border-acidGreen bg-acidGreen text-black" : "border-zinc-800 text-zinc-300"}`}
                >
                  全部主題
                </button>
                {topics.map((topic) => (
                  <button
                    type="button"
                    key={topic}
                    onClick={() => changeTopic(topic)}
                    className={`border px-3 py-2 text-left text-sm font-bold ${selectedTopic === topic ? "border-acidGreen bg-acidGreen text-black" : "border-zinc-800 text-zinc-300 hover:border-acidGreen"}`}
                  >
                    {topic}
                  </button>
                ))}
              </div>
            </aside>

            <section>
              {currentCard ? (
                <>
                  <div className="mb-3 flex items-center justify-between gap-4 text-xs font-black text-zinc-500">
                    <span>{currentCard.topic}</span>
                    <span>{cardIndex + 1} / {studyCards.length}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsRevealed((revealed) => !revealed)}
                    className="min-h-[390px] w-full border-2 border-flashYellow bg-[#101010] p-7 text-left shadow-[10px_10px_0_#ff3b30] transition hover:-translate-y-1 md:p-10"
                    aria-expanded={isRevealed}
                  >
                    <p className="text-xs font-black tracking-[0.16em] text-deepPink">{currentCard.Domain}</p>
                    <h2 className="mt-7 text-3xl font-black leading-tight text-white md:text-4xl">{currentCard.title}</h2>
                    {isRevealed ? (
                      <p className="mt-8 whitespace-pre-line border-t border-zinc-700 pt-7 text-base font-medium leading-8 text-zinc-200 md:text-lg">
                        {currentCard.Description}
                      </p>
                    ) : (
                      <p className="mt-10 text-sm font-black tracking-[0.18em] text-flashYellow">點擊卡牌查看解析</p>
                    )}
                  </button>

                  <div className="mt-7 grid grid-cols-3 gap-3">
                    <button type="button" onClick={() => moveCard(-1)} className="border-2 border-zinc-700 px-3 py-3 font-black hover:border-white">上一張</button>
                    <button
                      type="button"
                      onClick={() => toggleSaved(currentCard.id)}
                      className={`border-2 px-3 py-3 font-black ${currentCardIsSaved ? "border-deepPink bg-deepPink text-white" : "border-deepPink text-deepPink hover:bg-deepPink hover:text-white"}`}
                    >
                      {currentCardIsSaved ? "已存筆記" : "存成筆記"}
                    </button>
                    <button type="button" onClick={() => moveCard(1)} className="border-2 border-zinc-700 px-3 py-3 font-black hover:border-white">下一張</button>
                  </div>
                  {message ? <p className="mt-4 border-l-4 border-deepPink bg-[#170817] px-4 py-3 text-sm font-bold text-deepPink">{message}</p> : null}
                </>
              ) : (
                <p className="border border-zinc-800 p-6 text-zinc-400">這個分類目前沒有卡牌。</p>
              )}
            </section>
          </div>
        ) : (
          <section>
            <div className="mb-6 flex flex-wrap gap-2 border-b border-zinc-800 pb-6" aria-label="學習卡牌領域篩選">
              {domainOptions.map((domain) => {
                const count = domain.key === "all"
                  ? savedIds.length
                  : CLF_FLASHCARDS.filter((card) => savedIds.includes(card.id) && flashcardDomainKey(card.Domain) === domain.key).length;
                const selected = selectedDomain === domain.key;
                return (
                  <button
                    type="button"
                    key={domain.key}
                    onClick={() => setSelectedDomain(domain.key)}
                    className={`border px-4 py-3 text-sm font-black ${selected ? "border-flashYellow bg-flashYellow text-black" : "border-zinc-700 bg-black text-zinc-300 hover:border-flashYellow"}`}
                  >
                    {domain.label} <span className={selected ? "text-black/60" : "text-zinc-500"}>{count}</span>
                  </button>
                );
              })}
            </div>

            {noteCards.length ? (
              <div className="grid gap-5 md:grid-cols-2">
                {noteCards.map((card) => (
                  <article key={card.id} className="border-2 border-zinc-800 bg-[#101010] p-5 shadow-[6px_6px_0_#ff3b30]">
                    <div className="flex items-start justify-between gap-4">
                      <p className="text-xs font-black leading-5 text-deepPink">{card.Domain}</p>
                      <button type="button" onClick={() => toggleSaved(card.id)} className="shrink-0 border border-zinc-700 px-2 py-1 text-xs font-black text-zinc-400 hover:border-hotRed hover:text-hotRed">
                        刪除
                      </button>
                    </div>
                    <p className="mt-3 text-xs font-bold tracking-[0.12em] text-zinc-600">{card.content} · {card.topic}</p>
                    <h2 className="mt-4 text-xl font-black leading-8 text-white">{card.title}</h2>
                    <p className="mt-4 whitespace-pre-line border-l-4 border-flashYellow pl-4 text-sm leading-7 text-zinc-300">{card.Description}</p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="border-l-4 border-zinc-700 bg-[#101010] p-6">
                <p className="font-black text-zinc-200">目前還沒有卡牌</p>
                <p className="mt-2 text-sm leading-6 text-zinc-500">
                  {savedIds.length ? "這個領域目前沒有收藏卡牌，請切換其他領域。" : "前往學習卡牌，按下「存成筆記」即可收藏。"}
                </p>
              </div>
            )}
          </section>
        )}
      </section>
    </main>
  );
}
