"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { AlertTriangle, GaugeCircle, ShieldAlert, Sparkles, Waves } from "lucide-react";

import { ActivityFeed } from "@/components/activity-feed";
import { ActivityToastStack } from "@/components/activity-toast-stack";
import { LiveToolbar } from "@/components/live-toolbar";
import { DecisionBadge } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { postBrowserJson } from "@/lib/browser-api";
import {
  diffNewActivities,
  formatRelativeAge,
  formatTimeUntil,
  toastableActivities,
  type LiveActivity,
} from "@/lib/live-utils";
import { useLiveResource } from "@/lib/use-live-resource";

type OverviewLivePayload = {
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
  activities: LiveActivity[];
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

export function OverviewLiveShell({
  initialData,
}: {
  initialData: OverviewLivePayload;
}) {
  const [toasts, setToasts] = useState<Array<LiveActivity & { toastId: string }>>([]);
  const [controlMessage, setControlMessage] = useState<string | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const toastTimers = useRef<number[]>([]);

  const { data, error, isRefreshing, lastSuccessfulFetchAt, liveMode, refresh, setLiveMode } =
    useLiveResource<OverviewLivePayload>({
      path: "/api/proxy/dashboard/live?hours=24&recent_seconds=60&activity_limit=8",
      initialData,
      storageKey: "fraud-platform:overview-live-mode",
      onData(previous, current) {
        const incoming = toastableActivities(
          diffNewActivities(previous.activities ?? [], current.activities ?? []),
        ).slice(0, 3);
        for (const item of incoming) {
          const toastId = `${item.id}:${Date.now()}`;
          setToasts((currentToasts) => [{ ...item, toastId }, ...currentToasts].slice(0, 4));
          const timer = window.setTimeout(() => {
            setToasts((currentToasts) =>
              currentToasts.filter((toast) => toast.toastId !== toastId),
            );
          }, 4500);
          toastTimers.current.push(timer);
        }
      },
    });

  useEffect(() => {
    const timersRef = toastTimers;
    return () => {
      for (const timer of timersRef.current) {
        window.clearTimeout(timer);
      }
    };
  }, []);

  async function runControl(
    pendingLabel: string,
    actionLabel: string,
    path: string,
    body: Record<string, unknown> = {},
  ) {
    setPendingAction(pendingLabel);
    setControlError(null);
    setControlMessage(null);
    const result = await postBrowserJson<Record<string, unknown>>(`/api/proxy${path}`, body);
    if (result.error) {
      setControlError(result.error);
      setPendingAction(null);
      return;
    }
    setControlMessage(actionLabel);
    await refresh();
    setPendingAction(null);
  }

  return (
    <div className="space-y-6">
      <ActivityToastStack toasts={toasts} />

      <LiveToolbar
        liveMode={liveMode}
        lastSuccessfulFetchAt={lastSuccessfulFetchAt}
        onRefresh={() => {
          void refresh();
        }}
        onToggleLiveMode={setLiveMode}
        isRefreshing={isRefreshing}
        sources={["API", "DB", "Model cache", "Producer controls"]}
      />

      {error ? (
        <div className="rounded-2xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
          Live refresh warning: {error}
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Transactions"
          value={data.summary.total_transactions.toString()}
          detail={`+${data.recent_window.processed_transactions} in the last ${data.recent_window.window_seconds}s`}
          icon={Waves}
        />
        <MetricCard
          label="Blocked"
          value={data.summary.blocked_transactions.toString()}
          detail={`+${data.recent_window.blocked_transactions} in the last ${data.recent_window.window_seconds}s`}
          icon={ShieldAlert}
        />
        <MetricCard
          label="Review Decisions"
          value={data.summary.review_transactions.toString()}
          detail={`+${data.recent_window.review_transactions} in the last ${data.recent_window.window_seconds}s`}
          icon={AlertTriangle}
        />
        <MetricCard
          label="Average Score"
          value={data.summary.average_score.toFixed(3)}
          detail="persisted hybrid rule + model score"
          icon={GaugeCircle}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <SignalCard
          label="Open review backlog"
          value={data.recent_window.open_review_backlog.toString()}
          detail="Current analyst-open REVIEW cases"
        />
        <SignalCard
          label="Producer"
          value={
            data.producer.available
              ? data.producer.running
                ? "running"
                : "paused"
              : "unavailable"
          }
          detail={
            data.producer.available
              ? `${(data.producer.current_rate_per_second ?? 0).toFixed(1)} evt/s • ${(data.producer.current_fraud_ratio ?? 0).toFixed(2)} fraud ratio`
              : data.producer.error ?? "Producer service is not reachable."
          }
        />
        <SignalCard
          label="Worker"
          value={
            data.worker.available ? (data.worker.healthy ? "healthy" : "degraded") : "unavailable"
          }
          detail={
            data.worker.available
              ? data.worker.running
                ? "Bytewax stream worker is consuming live traffic."
                : "Worker is reachable but not running."
              : data.worker.error ?? "Worker service is not reachable."
          }
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <div className="space-y-6">
          <ActivityFeed
            title="Live activity"
            description="Real decisions and feedback events detected from the persisted case timeline."
            activities={data.activities}
            emptyText="Once the pipeline persists decisions or feedback, the latest activity will appear here."
          />

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle>Decision trend</CardTitle>
                <Badge variant="neutral" className="w-fit">
                  DB
                </Badge>
              </div>
              <CardDescription>
                Hourly decision counts over the analytics window. This section is refresh-driven in live mode.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.trends.length === 0 ? (
                <p className="text-sm text-muted">
                  No trend buckets yet. Keep the producer running and this view will fill in.
                </p>
              ) : (
                data.trends.map((item) => (
                  <div
                    key={`${item.bucket}-${item.decision}`}
                    className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">
                          {new Date(item.bucket).toLocaleString()}
                        </p>
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
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle>Demo controls</CardTitle>
                <Badge variant="neutral" className="w-fit">
                  API → Producer → Kafka
                </Badge>
              </div>
              <CardDescription>
                Every action below triggers real producer behavior. The resulting cases flow through Kafka,
                Bytewax, Redis, scoring, and Postgres.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <ControlButton
                  label="Inject card testing burst"
                  onClick={() =>
                    void runControl(
                      "Inject card testing burst",
                      "Injected card testing burst",
                      "/demo/producer/burst",
                      {
                        scenario: "card_testing",
                        count: 12,
                      },
                    )
                  }
                  pending={pendingAction === "Inject card testing burst"}
                />
                <ControlButton
                  label="Inject impossible travel burst"
                  onClick={() =>
                    void runControl(
                      "Inject impossible travel burst",
                      "Injected impossible travel burst",
                      "/demo/producer/burst",
                      {
                        scenario: "impossible_travel",
                        count: 10,
                      },
                    )
                  }
                  pending={pendingAction === "Inject impossible travel burst"}
                />
                <ControlButton
                  label="Inject new-device high-amount burst"
                  onClick={() =>
                    void runControl(
                      "Inject new-device high-amount burst",
                      "Injected new-device burst",
                      "/demo/producer/burst",
                      {
                        scenario: "new_device_high_amount",
                        count: 10,
                      },
                    )
                  }
                  pending={pendingAction === "Inject new-device high-amount burst"}
                />
                <ControlButton
                  label={data.producer.running ? "Pause producer" : "Resume producer"}
                  onClick={() =>
                    void runControl(
                      data.producer.running ? "Pause producer" : "Resume producer",
                      data.producer.running ? "Producer paused" : "Producer resumed",
                      data.producer.running ? "/demo/producer/stop" : "/demo/producer/start",
                    )
                  }
                  pending={
                    pendingAction === (data.producer.running ? "Pause producer" : "Resume producer")
                  }
                />
                <ControlButton
                  label="Boost fraud ratio for 30s"
                  onClick={() =>
                    void runControl(
                      "Boost fraud ratio for 30s",
                      "Boosted fraud ratio for 30s",
                      "/demo/producer/boost",
                      {
                        fraud_ratio: 0.68,
                        rate_per_second: 6.0,
                        duration_seconds: 30,
                      },
                    )
                  }
                  pending={pendingAction === "Boost fraud ratio for 30s"}
                />
                <ControlButton
                  label="Reset to normal flow"
                  onClick={() =>
                    void runControl(
                      "Reset to normal flow",
                      "Producer reset to baseline",
                      "/demo/producer/reset",
                    )
                  }
                  pending={pendingAction === "Reset to normal flow"}
                />
              </div>
              {controlMessage ? (
                <p className="text-sm text-accent">{controlMessage}</p>
              ) : null}
              {controlError ? (
                <p className="text-sm text-danger">{controlError}</p>
              ) : null}
              {data.producer.override_expires_at ? (
                <p className="text-xs text-muted">
                  Temporary producer profile {formatTimeUntil(data.producer.override_expires_at)}
                </p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle>Current model</CardTitle>
                <Badge variant="neutral" className="w-fit">
                  Model registry cache
                </Badge>
              </div>
              <CardDescription>
                Champion metadata loaded through the API from the local registry cache and MLflow fallback.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {data.model ? (
                <>
                  <Signal label="Model" value={`${data.model.model_name}@${data.model.model_alias}`} />
                  <Signal label="Version" value={data.model.model_version} />
                  <Signal label="Review threshold" value={data.model.review_threshold.toFixed(2)} />
                  <Signal label="Block threshold" value={data.model.block_threshold.toFixed(2)} />
                </>
              ) : (
                <p className="text-sm text-muted">
                  No champion model is registered yet. Run the trainer bootstrap flow to create one.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle>Story links</CardTitle>
                <Badge variant="neutral" className="w-fit">
                  Grafana + cases
                </Badge>
              </div>
              <CardDescription>
                Pivot from analyst actions into the case backlog or observability view during the demo.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <ActionLink href="/cases" label="Open the analyst backlog" />
              <ActionLink href="/monitoring" label="Open monitoring context" />
              <a
                href={data.grafana_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between rounded-2xl border border-border/70 bg-panelMuted/40 px-4 py-3 text-sm transition hover:border-accent/30 hover:bg-accent/10"
              >
                <span>Open Grafana</span>
                <Sparkles className="h-4 w-4 text-accent" />
              </a>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
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
  icon: typeof Waves;
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

function SignalCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <Card>
      <CardContent className="space-y-2 p-5">
        <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
        <p className="text-2xl font-semibold">{value}</p>
        <p className="text-sm text-muted">{detail}</p>
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

function ControlButton({
  label,
  onClick,
  pending,
}: {
  label: string;
  onClick: () => void;
  pending: boolean;
}) {
  return (
    <Button
      type="button"
      variant="secondary"
      className="min-h-12 justify-start whitespace-normal text-left"
      onClick={onClick}
      disabled={pending}
    >
      {pending ? "Working…" : label}
    </Button>
  );
}

function ActionLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="flex items-center justify-between rounded-2xl border border-border/70 bg-panelMuted/40 px-4 py-3 text-sm transition hover:border-accent/30 hover:bg-accent/10"
    >
      <span>{label}</span>
      <Sparkles className="h-4 w-4 text-accent" />
    </Link>
  );
}
