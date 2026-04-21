import { ConsoleShell } from "@/components/console-shell";
import { EmptyState } from "@/components/empty-state";
import { fetchJson } from "@/lib/api";

import { CasesLiveShell } from "./cases-live-shell";

type CasesPayload = {
  items: Array<{
    case_id: string;
    transaction_id: string;
    decision: string;
    status: string;
    decision_time: string;
    score: number | null;
    scenario: string | null;
    amount: number | null;
    country: string | null;
    channel: string | null;
    account_id: string | null;
  }>;
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
  live_window: {
    window_seconds: number;
    matching_cases: number;
    blocked_cases: number;
    review_cases: number;
    last_updated_at: string;
  };
  activities: Array<{
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
  }>;
};

export default async function CasesPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = (await searchParams) ?? {};
  const page = typeof params.page === "string" ? params.page : "1";
  const status = typeof params.status === "string" ? params.status : "open";
  const decision = typeof params.decision === "string" ? params.decision : "REVIEW";
  const search = typeof params.search === "string" ? params.search : "";
  const sortOrder = typeof params.sort_order === "string" ? params.sort_order : "desc";

  const query = new URLSearchParams({
    page,
    page_size: "20",
    sort_by: "decision_time",
    sort_order: sortOrder,
    recent_seconds: "30",
    activity_limit: "6",
  });
  if (status) query.set("status", status);
  if (decision) query.set("decision", decision);
  if (search) query.set("search", search);

  const cases = await fetchJson<CasesPayload>(`/cases/live?${query.toString()}`);

  return (
    <ConsoleShell
      section="cases"
      title="Analyst backlog"
      subtitle="Live review queue sourced from persisted fraud decisions. The page defaults to open REVIEW cases so the demo matches the real analyst workflow."
    >
      {cases.error || !cases.data ? (
        <EmptyState
          title="Backlog is unavailable"
          description={cases.error ?? "The cases API returned no data."}
        />
      ) : (
        <CasesLiveShell
          initialData={cases.data}
          initialParams={{ page, search, status, decision, sortOrder }}
        />
      )}
    </ConsoleShell>
  );
}
