import { Draft } from "@/types";

const HISTORY_KEY = "pg_draft_history";
const MAX_ENTRIES = 50;

export function loadHistory(): Draft[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as Draft[];
  } catch {
    return [];
  }
}

function persist(drafts: Draft[]): void {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(drafts));
}

export function saveToHistory(draft: Draft): void {
  const existing = loadHistory().filter((d) => d.id !== draft.id);
  persist([draft, ...existing].slice(0, MAX_ENTRIES));
}

/** Replace an existing entry by id (e.g. after verify / decision). */
export function updateInHistory(draft: Draft): void {
  const existing = loadHistory();
  const idx = existing.findIndex((d) => d.id === draft.id);
  if (idx === -1) {
    // Not yet saved — save it now
    persist([draft, ...existing].slice(0, MAX_ENTRIES));
  } else {
    existing[idx] = draft;
    persist(existing);
  }
}

export function deleteFromHistory(id: string): void {
  persist(loadHistory().filter((d) => d.id !== id));
}

export function clearHistory(): void {
  localStorage.removeItem(HISTORY_KEY);
}
