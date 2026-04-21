import Link from "next/link";

import { ConsoleShell } from "@/components/console-shell";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
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
  recent_window: {
    window_seconds: number;
    processed_transactions: number;
    blocked_transactions: number;
    review_transactions: number;
    open_review_backlog: number;
  };
  grafana_url: string;
  producer: {
    available: boolean;
    running?: boolean;
    current_rate_per_second?: number;
    current_fraud_ratio?: number;
    error?: string;
  };
  worker: {
    available: boolean;
    running?: boolean;
    healthy?: boolean;
    error?: string;
  };
};

export default async function MonitoringPage() {
  const live = await fetchJson<MonitoringPayload>("/dashboard/live");
  const health = await fetchJson<{
    status: string;
    dependencies: Array<{ name: string; healthy: boolean; detail?: string }>;
  }>("/health/ready");

  return (
    <ConsoleShell
      section="monitoring"
      title="Monitoring, provenance, and observability"
      subtitle="This page separates API readiness, DB-backed business activity, and the Grafana/Prometheus observability layer so the demo story stays honest."
    >
      {live.error || !live.data ? (
        <EmptyState
          title="Monitoring data unavailable"
          description={live.error ?? "The live dashboard endpoint is not returning data yet."}
        />
      ) : (
        <div className="space-y-6">
          <section className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle>API readiness and dependencies</CardTitle>
                  <Badge variant="neutral" className="w-fit">
                    Readiness endpoint
                  </Badge>
                </div>
                <CardDescription>
                  These cards come from FastAPI health checks, not from Prometheus dashboards.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {health.data ? (
                  health.data.dependencies.map((item) => (
                    <div
                      key={item.name}
                      className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium">{item.name}</p>
                        <p
                          className={`text-xs uppercase tracking-[0.24em] ${
                            item.healthy ? "text-accent" : "text-danger"
                          }`}
                        >
                          {item.healthy ? "healthy" : "degraded"}
                        </p>
                      </div>
                      {item.detail ? <p className="mt-2 text-sm text-muted">{item.detail}</p> : null}
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted">
                    {health.error ?? "Health payload unavailable."}
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle>Business flow snapshot</CardTitle>
                  <Badge variant="neutral" className="w-fit">
                    API → Postgres
                  </Badge>
                </div>
                <CardDescription>
                  These numbers summarize persisted fraud activity, not infra metrics.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2">
                <Metric label="Transactions (24h)" value={String(live.data.summary.total_transactions)} />
                <Metric label="Blocked (24h)" value={String(live.data.summary.blocked_transactions)} />
                <Metric label="Review decisions (24h)" value={String(live.data.summary.review_transactions)} />
                <Metric label="Open review backlog" value={String(live.data.recent_window.open_review_backlog)} />
                <Metric label={`Transactions (${live.data.recent_window.window_seconds}s)`} value={String(live.data.recent_window.processed_transactions)} />
                <Metric label="Average score" value={live.data.summary.average_score.toFixed(3)} />
              </CardContent>
            </Card>
          </section>

          <section className="grid gap-6 xl:grid-cols-[0.9fr,1.1fr]">
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle>Pipeline operators</CardTitle>
                  <Badge variant="neutral" className="w-fit">
                    Producer + worker
                  </Badge>
                </div>
                <CardDescription>
                  This is the bridge between the analyst console and the streaming system behind it.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <OperatorCard
                  title="Producer"
                  state={
                    live.data.producer.available
                      ? live.data.producer.running
                        ? "running"
                        : "paused"
                      : "unavailable"
                  }
                  detail={
                    live.data.producer.available
                      ? `${(live.data.producer.current_rate_per_second ?? 0).toFixed(1)} evt/s • ${(live.data.producer.current_fraud_ratio ?? 0).toFixed(2)} fraud ratio`
                      : live.data.producer.error ?? "Producer service unavailable."
                  }
                />
                <OperatorCard
                  title="Stream worker"
                  state={
                    live.data.worker.available
                      ? live.data.worker.healthy
                        ? "healthy"
                        : "degraded"
                      : "unavailable"
                  }
                  detail={
                    live.data.worker.available
                      ? live.data.worker.running
                        ? "Bytewax is actively consuming the stream."
                        : "Worker is reachable but not running."
                      : live.data.worker.error ?? "Worker service unavailable."
                  }
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle>Grafana and Prometheus</CardTitle>
                  <Badge variant="neutral" className="w-fit">
                    Observability
                  </Badge>
                </div>
                <CardDescription>
                  Grafana is the separate operator surface for throughput, latency, DLQ, and alerting. The analyst console is not pretending to be Grafana.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted">Grafana</p>
                  <p className="mt-2 text-sm font-medium">{live.data.grafana_url}</p>
                </div>
                <div className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-muted">How to explain it</p>
                  <p className="mt-2 text-sm text-muted">
                    Use this console for fraud cases and analyst workflow. Open Grafana when you want to show system throughput, Prometheus metrics, alert state, and drift operations.
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Link
                    href={live.data.grafana_url}
                    className="rounded-2xl bg-accent px-4 py-3 text-sm font-medium text-background transition hover:bg-accent/90"
                  >
                    Open Grafana
                  </Link>
                  <Link
                    href={`${process.env.API_PUBLIC_BASE_URL ?? "http://localhost:8000"}/metrics`}
                    className="rounded-2xl border border-border px-4 py-3 text-sm font-medium transition hover:bg-panelMuted/50"
                  >
                    Open API metrics
                  </Link>
                </div>
              </CardContent>
            </Card>
          </section>
        </div>
      )}
    </ConsoleShell>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-panelMuted/35 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
      <p className="mt-2 text-sm font-medium break-all">{value}</p>
    </div>
  );
}

function OperatorCard({
  title,
  state,
  detail,
}: {
  title: string;
  state: string;
  detail: string;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs uppercase tracking-[0.24em] text-muted">{state}</p>
      </div>
      <p className="mt-2 text-sm text-muted">{detail}</p>
    </div>
  );
}
