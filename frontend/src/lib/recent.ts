const KEY = "xplore.recent.v1";
const MAX = 8;

export interface RecentExperiment {
  id: string;
  savedAt: string;
  label: string;
}

export function loadRecent(): RecentExperiment[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(parsed) ? (parsed as RecentExperiment[]) : [];
  } catch {
    return [];
  }
}

export function rememberExperiment(entry: RecentExperiment): RecentExperiment[] {
  const next = [entry, ...loadRecent().filter((e) => e.id !== entry.id)].slice(0, MAX);
  localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}
