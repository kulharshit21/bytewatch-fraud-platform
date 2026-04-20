import Link from "next/link";
import { ArrowRight, BarChart3, Clock3, ShieldAlert, WalletCards } from "lucide-react";

import { ConsoleShell } from "@/components/console-shell";
import { EmptyState } from "@/components/empty-state";
import { DecisionBadge } from "@/components/status";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchJson } from "@/lib/api";

type OverviewPayload = {
  summary: {
    total_transactions: number;
    blocked_transactions: number;
    review_transactions: number;
    approved_transactions: number;
    average_score: number;
    last_updated_at: string;
  };
  trends: Array<{ bucket: string; decision: string; count: number }>;
  model: {
    model_name: string;
    model_version: string;
    model_alias: string;
    review_threshold: number;
    block_threshold: number;
  } | null;
  grafana_url: string;
};

export default async function OverviewPage() {
  const overview = await fetchJson<OverviewPayload>("/dashboard/overview");

  return (
    <ConsoleShell
      section="overview"
      title="Streaming fraud operations at a glance"
      subtitle="Live overview of decisions, case pressure, model thresholds, and recent decision activity sourced from the FastAPI analytics layer."
    >
      {overview.error || !overview.data ? (
        <EmptyState
          title="Overview is waiting on the backend"
          description={overview.error ?? "The API is reachable but no dashboard payload was returned yet."}
        />
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Transactions"
              value={overview.data.summary.total_transactions.toString()}
              detail="processed in current analytics window"
              icon={BarChart3}
            />
            <MetricCard
              label="Blocked"
              value={overview.data.summary.blocked_transactions.toString()}
              detail="transactions auto-blocked"
              icon={ShieldAlert}
            />
            <MetricCard
              label="Review Queue"
              value={overview.data.summary.review_transactions.toString()}
              detail="cases routed for analyst review"
              icon={Clock3}
            />
            <MetricCard
              label="Average Score"
              value={overview.data.summary.average_score.toFixed(3)}
              detail="hybrid rule + model score"
              icon={WalletCards}
            />
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.5fr,1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Decision Trend</CardTitle>
                <CardDescription>Hourly decision counts over the selected analytics window.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {overview.data.trends.length === 0 ? (
                  <p className="text-sm text-muted">No trend buckets yet. Once transactions are processed, they will appear here automatically.</p>
                ) : (
                  overview.data.trends.map((item) => (
                    <div key={`${item.bucket}-${item.decision}`} className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">{new Date(item.bucket).toLocaleString()}</p>
                          <div className="mt-2">
                            <DecisionBadge decision={item.decision} />
                          </div>
                        </div>
                        <p className="text-2xl font-semibold">{item.count}</p>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <div className="grid gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Current Model</CardTitle>
                  <CardDescription>Champion metadata loaded by the API from MLflow and local cache.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {overview.data.model ? (
                    <>
                      <Signal label="Model" value={`${overview.data.model.model_name}@${overview.data.model.model_alias}`} />
                      <Signal label="Version" value={overview.data.model.model_version} />
                      <Signal label="Review Threshold" value={overview.data.model.review_threshold.toFixed(2)} />
                      <Signal label="Block Threshold" value={overview.data.model.block_threshold.toFixed(2)} />
                    </>
                  ) : (
                    <p className="text-sm leading-6 text-muted">No champion model is registered yet. Use the trainer bootstrap flow to create one.</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Next Moves</CardTitle>
                  <CardDescription>Quick pivots for demo and operator review.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <ActionLink href="/cases" label="Open analyst queue" />
                  <ActionLink href="/models" label="Inspect model registry snapshot" />
                  <ActionLink href="/monitoring" label="Open monitoring and Grafana links" />
                </CardContent>
              </Card>
            </div>
          </section>
        </>
      )}
    </ConsoleShell>
  );
}

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: typeof BarChart3;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between p-6">
        <div className="space-y-3">
          <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
          <p className="text-3xl font-semibold tracking-tight">{value}</p>
          <p className="text-sm text-muted">{detail}</p>
        </div>
        <div className="rounded-2xl border border-border bg-background/50 p-3 text-accent">
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}

function Signal({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-border/70 pb-4 last:border-b-0 last:pb-0">
      <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
      <p className="mt-2 text-sm font-medium">{value}</p>
    </div>
  );
}

function ActionLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="flex items-center justify-between rounded-2xl border border-border/70 bg-panelMuted/40 px-4 py-3 text-sm transition-colors hover:border-accent/30 hover:bg-accent/10"
    >
      <span>{label}</span>
      <ArrowRight className="h-4 w-4 text-accent" />
    </Link>
  );
}
