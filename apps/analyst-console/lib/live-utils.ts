export type LiveActivity = {
  id: string;
  type: string;
  timestamp: string;
  case_id?: string;
  transaction_id?: string;
  decision?: string;
  status?: string;
  score?: number | null;
  scenario?: string | null;
  rule_id?: string | null;
  feedback_label?: string;
  analyst_id?: string;
  message: string;
};

export function diffNewActivities(
  previous: LiveActivity[],
  current: LiveActivity[],
): LiveActivity[] {
  const previousIds = new Set(previous.map((item) => item.id));
  return current.filter((item) => !previousIds.has(item.id));
}

export function toastableActivities(items: LiveActivity[]): LiveActivity[] {
  return items.filter((item) => {
    if (item.type === "feedback") {
      return true;
    }
    const decision = item.decision?.toUpperCase();
    return decision === "BLOCK" || decision === "REVIEW" || (item.score ?? 0) >= 0.9;
  });
}

export function recentDecision(timestamp: string, windowSeconds: number, now = Date.now()) {
  return now - new Date(timestamp).getTime() <= windowSeconds * 1000;
}

export function formatRelativeAge(timestamp: string, now = Date.now()) {
  const seconds = Math.max(0, Math.round((now - new Date(timestamp).getTime()) / 1000));
  if (seconds < 5) {
    return "updated just now";
  }
  if (seconds < 60) {
    return `updated ${seconds}s ago`;
  }
  const minutes = Math.round(seconds / 60);
  return `updated ${minutes}m ago`;
}

export function formatTimeUntil(timestamp: string, now = Date.now()) {
  const seconds = Math.max(0, Math.round((new Date(timestamp).getTime() - now) / 1000));
  if (seconds < 5) {
    return "expires in a few seconds";
  }
  if (seconds < 60) {
    return `expires in ${seconds}s`;
  }
  const minutes = Math.round(seconds / 60);
  return `expires in ${minutes}m`;
}

export function formatScenarioLabel(scenario: string | null | undefined) {
  if (!scenario) {
    return "unknown scenario";
  }
  return scenario
    .replaceAll("_", " ")
    .replaceAll("fraud", "")
    .replace(/\s+/g, " ")
    .trim();
}
