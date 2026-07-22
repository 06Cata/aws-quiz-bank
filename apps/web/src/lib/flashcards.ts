export type FlashcardExam = "clf" | "saa";
export type FlashcardDomainKey = "all" | "domain_1" | "domain_2" | "domain_3" | "domain_4";

export type Flashcard = {
  id: string;
  source_key: string;
  chapter_key: string;
  chapter_order: number;
  topic: string;
  title: string;
  exam_domain: string;
  description: string;
};

export type FlashcardNote = Flashcard & {
  note_id: string;
  created_at?: string;
};

type FlashcardExamConfig = {
  name: string;
  shortName: string;
  apiPrefix: string;
  domains: Array<{
    key: Exclude<FlashcardDomainKey, "all">;
    label: string;
  }>;
};

export const FLASHCARD_EXAMS: Record<FlashcardExam, FlashcardExamConfig> = {
  clf: {
    name: "AWS Cloud Practitioner",
    shortName: "Cloud Practitioner",
    apiPrefix: "/api",
    domains: [
      { key: "domain_1", label: "領域 1｜雲端概念" },
      { key: "domain_2", label: "領域 2｜安全與合規" },
      { key: "domain_3", label: "領域 3｜雲端技術與服務" },
      { key: "domain_4", label: "領域 4｜計費、定價與支援" }
    ]
  },
  saa: {
    name: "AWS Solutions Architect Associate",
    shortName: "Solutions Architect Associate",
    apiPrefix: "/api/saa",
    domains: [
      { key: "domain_1", label: "領域 1｜設計彈性架構" },
      { key: "domain_2", label: "領域 2｜設計高性能架構" },
      { key: "domain_3", label: "領域 3｜設計安全架構" },
      { key: "domain_4", label: "領域 4｜設計成本優化架構" }
    ]
  }
};

export function flashcardDomainKey(domain: string): Exclude<FlashcardDomainKey, "all"> | null {
  const normalized = domain.toLowerCase();
  for (const domainNumber of [1, 2, 3, 4] as const) {
    if (normalized.includes(`領域 ${domainNumber}`) || normalized.includes(`domain ${domainNumber}`)) {
      return `domain_${domainNumber}`;
    }
  }
  return null;
}
