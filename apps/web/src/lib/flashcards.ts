import flashcardDocument from "../../../../cards/clf_flashcards.json";

export type FlashcardSource = {
  Domain: string;
  Description: string;
};

export type Flashcard = FlashcardSource & {
  id: string;
  content: string;
  topic: string;
  title: string;
};

export type FlashcardDomainKey = "all" | "domain_1" | "domain_2" | "domain_3" | "domain_4";

type FlashcardDocument = Record<string, Record<string, Record<string, FlashcardSource>>>;

export const FLASHCARD_NOTE_STORAGE_KEY = "aws-quiz-flashcard-notes-v1";

export const CLF_FLASHCARD_DOMAINS: Array<{
  key: Exclude<FlashcardDomainKey, "all">;
  label: string;
}> = [
  { key: "domain_1", label: "領域 1｜雲端概念" },
  { key: "domain_2", label: "領域 2｜安全與合規" },
  { key: "domain_3", label: "領域 3｜雲端技術與服務" },
  { key: "domain_4", label: "領域 4｜計費、定價與支援" }
];

const document = flashcardDocument as FlashcardDocument;

export const FLASHCARD_CONTENTS = Object.keys(document).sort((left, right) =>
  left.localeCompare(right, undefined, { numeric: true })
);

export const CLF_FLASHCARDS: Flashcard[] = FLASHCARD_CONTENTS.flatMap((content) =>
  Object.entries(document[content] ?? {}).flatMap(([topic, cards]) =>
    Object.entries(cards).map(([title, card]) => ({
      ...card,
      id: `${content}::${topic}::${title}`,
      content,
      topic,
      title
    }))
  )
);

export function flashcardDomainKey(domain: string): Exclude<FlashcardDomainKey, "all"> | null {
  const normalized = domain.toLowerCase();
  for (const domainNumber of [1, 2, 3, 4] as const) {
    if (normalized.includes(`領域 ${domainNumber}`) || normalized.includes(`domain ${domainNumber}`)) {
      return `domain_${domainNumber}`;
    }
  }
  return null;
}

export function readSavedFlashcardIds(): string[] {
  try {
    const value = window.localStorage.getItem(FLASHCARD_NOTE_STORAGE_KEY);
    const parsed: unknown = value ? JSON.parse(value) : [];
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [];
  } catch {
    return [];
  }
}

export function writeSavedFlashcardIds(ids: string[]) {
  window.localStorage.setItem(FLASHCARD_NOTE_STORAGE_KEY, JSON.stringify(ids));
}
