import { ConsoleShell } from "@/components/console-shell";
import { EmptyState } from "@/components/empty-state";
import { fetchJson } from "@/lib/api";

import { OverviewLiveShell } from "./overview-live-shell";

type OverviewPayload = {
  summary: {
    total_transactions: number;
    blocked_transactions: number;
    review_transactions: number;
    approved_transactions: number;
    average_score: number;
    last_updated_at: string;
  };
  recent_window: {
    window_seconds: number;
    processed_transactions: number;
    blocked_transactions: number;
    review_transactions: number;
    open_review_backlog: number;
    last_updated_at: string;
  };
  trends: Array<{ bucket: string; decision: string; count: number }>;
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
  model: {
    model_name: string;
    model_version: string;
    model_alias: string;
    review_threshold: number;
    block_threshold: number;
  } | null;
  grafana_url: string;
  producer: {
    available: boolean;
    running?: boolean;
    generated_events?: number;
    current_rate_per_second?: number;
    current_fraud_ratio?: number;
    override_expires_at?: string | null;
    error?: string;
  };
  worker: {
    available: boolean;
    running?: boolean;
    healthy?: boolean;
    error?: string;
  };
};

export default async function OverviewPage() {
  const overview = await fetchJson<OverviewPayload>("/dashboard/live");

  return (
    <ConsoleShell
      section="overview"
      title="Streaming fraud operations at a glance"
      subtitle="Live analyst view of persisted decisions, backlog pressure, producer controls, and recent fraud activity sourced from the real FastAPI platform."
    >
      {overview.error || !overview.data ? (
        <EmptyState
          title="Overview is waiting on the backend"
          description={overview.error ?? "The API is reachable but no live dashboard payload was returned yet."}
        />
      ) : (
        <OverviewLiveShell initialData={overview.data} />
      )}
    </ConsoleShell>
  );
}
