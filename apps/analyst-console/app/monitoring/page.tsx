import Link from "next/link";

import { ConsoleShell } from "@/components/console-shell";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchJson } from "@/lib/api";

type MonitoringPayload = {
  summary: {
    total_transactions: number;
    blocked_transactions: number;
    review_transactions: number;
    average_score: number;
    last_updated_at: string;
  };
  grafana_url: string;
};

export default async function MonitoringPage() {
  const overview = await fetchJson<MonitoringPayload>("/dashboard/overview");
  const health = await fetchJson<{ status: string; dependencies: Array<{ name: string; healthy: boolean; detail?: string }> }>("/health/ready");

  return (
    <ConsoleShell
      section="monitoring"
      title="Monitoring and operator health"
      subtitle="Operational view across service readiness, persisted activity, and the provisioned Grafana workspace."
    >
      {overview.error || !overview.data ? (
        <EmptyState
          title="Monitoring data unavailable"
          description={overview.error ?? "The dashboard overview endpoint is not returning data yet."}
        />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
          <Card>
            <CardHeader>
              <CardTitle>Service readiness</CardTitle>
              <CardDescription>Current API dependency health reported by the live readiness endpoint.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {health.data ? (
                health.data.dependencies.map((item) => (
                  <div key={item.name} className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium">{item.name}</p>
                      <p className={`text-xs uppercase tracking-[0.24em] ${item.healthy ? "text-accent" : "text-danger"}`}>
                        {item.healthy ? "healthy" : "degraded"}
                      </p>
                    </div>
                    {item.detail ? <p className="mt-2 text-sm text-muted">{item.detail}</p> : null}
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted">{health.error ?? "Health payload unavailable."}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Grafana and metrics</CardTitle>
              <CardDescription>Use Grafana for Prometheus-backed dashboards and alert inspection.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-muted">Grafana</p>
                <p className="mt-2 text-sm font-medium">{overview.data.grafana_url}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-muted">Transactions</p>
                <p className="mt-2 text-sm font-medium">{overview.data.summary.total_transactions}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-muted">Blocked</p>
                <p className="mt-2 text-sm font-medium">{overview.data.summary.blocked_transactions}</p>
              </div>
              <div className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-muted">Review</p>
                <p className="mt-2 text-sm font-medium">{overview.data.summary.review_transactions}</p>
              </div>
              <Link
                href={overview.data.grafana_url}
                className="block rounded-2xl bg-accent px-4 py-3 text-center text-sm font-medium text-background transition hover:bg-accent/90"
              >
                Open Grafana
              </Link>
            </CardContent>
          </Card>
        </div>
      )}
    </ConsoleShell>
  );
}
