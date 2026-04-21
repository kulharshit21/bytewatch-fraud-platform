"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ActivityToastStack } from "@/components/activity-toast-stack";
import { LiveToolbar } from "@/components/live-toolbar";
import { DecisionBadge } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { diffNewActivities, formatScenarioLabel, recentDecision, toastableActivities, type LiveActivity } from "@/lib/live-utils";
import { useLiveResource } from "@/lib/use-live-resource";
import { cn } from "@/lib/utils";

type CasesLivePayload = {
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
  activities: LiveActivity[];
};

export function CasesLiveShell({
  initialData,
  initialParams,
}: {
  initialData: CasesLivePayload;
  initialParams: {
    page: string;
    search: string;
    status: string;
    decision: string;
    sortOrder: string;
  };
}) {
  const [toasts, setToasts] = useState<Array<LiveActivity & { toastId: string }>>([]);
  const [freshRowIds, setFreshRowIds] = useState<Record<string, number>>({});
  const toastTimers = useRef<number[]>([]);
  const queryString = buildLiveQuery(initialParams);
  const backlogMode =
    initialParams.status === "open" &&
    initialParams.decision === "REVIEW" &&
    initialParams.search.length === 0;

  const { data, error, isRefreshing, lastSuccessfulFetchAt, liveMode, refresh, setLiveMode } =
    useLiveResource<CasesLivePayload>({
      path: `/api/proxy/cases/live?${queryString}`,
      initialData,
      storageKey: "fraud-platform:cases-live-mode",
      onData(previous, current) {
        const knownCaseIds = new Set(previous.items.map((item) => item.case_id));
        const arriving = current.items.filter((item) => !knownCaseIds.has(item.case_id));
        if (arriving.length > 0) {
          const highlightUntil = Date.now() + 6000;
          setFreshRowIds((currentIds) => ({
            ...currentIds,
            ...Object.fromEntries(arriving.map((item) => [item.case_id, highlightUntil])),
          }));
        }

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
    const interval = window.setInterval(() => {
      const now = Date.now();
      setFreshRowIds((current) =>
        Object.fromEntries(
          Object.entries(current).filter(([, expiresAt]) => expiresAt > now),
        ),
      );
    }, 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const timersRef = toastTimers;
    return () => {
      for (const timer of timersRef.current) {
        window.clearTimeout(timer);
      }
    };
  }, []);

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
        sources={["API", "DB", backlogMode ? "Open review backlog" : "Filtered case query"]}
      />

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>Backlog controls</CardTitle>
            <Badge variant="neutral" className="w-fit">
              Query → API → Postgres
            </Badge>
          </div>
          <CardDescription>
            Defaults to open REVIEW cases so the page matches the real analyst backlog. Change filters only when
            you want to inspect the wider case stream.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 lg:grid-cols-[1.2fr,0.7fr,0.7fr,0.7fr,auto]">
            <label className="space-y-2 text-sm">
              <span className="text-muted">Search transaction</span>
              <input
                name="search"
                defaultValue={initialParams.search}
                className="w-full rounded-2xl border border-border bg-panelMuted/40 px-4 py-3 text-sm outline-none ring-0 transition focus:border-accent/40"
                placeholder="txn_00000042"
              />
            </label>
            <label className="space-y-2 text-sm">
              <span className="text-muted">Status</span>
              <select
                name="status"
                defaultValue={initialParams.status}
                className="w-full rounded-2xl border border-border bg-panelMuted/40 px-4 py-3 text-sm outline-none transition focus:border-accent/40"
              >
                <option value="">All</option>
                <option value="open">Open</option>
                <option value="closed">Closed</option>
              </select>
            </label>
            <label className="space-y-2 text-sm">
              <span className="text-muted">Decision</span>
              <select
                name="decision"
                defaultValue={initialParams.decision}
                className="w-full rounded-2xl border border-border bg-panelMuted/40 px-4 py-3 text-sm outline-none transition focus:border-accent/40"
              >
                <option value="">All</option>
                <option value="APPROVE">Approve</option>
                <option value="REVIEW">Review</option>
                <option value="BLOCK">Block</option>
              </select>
            </label>
            <label className="space-y-2 text-sm">
              <span className="text-muted">Sort order</span>
              <select
                name="sort_order"
                defaultValue={initialParams.sortOrder}
                className="w-full rounded-2xl border border-border bg-panelMuted/40 px-4 py-3 text-sm outline-none transition focus:border-accent/40"
              >
                <option value="desc">Newest first</option>
                <option value="asc">Oldest first</option>
              </select>
            </label>
            <div className="flex items-end">
              <button className="rounded-2xl bg-accent px-5 py-3 text-sm font-medium text-background transition hover:bg-accent/90">
                Apply
              </button>
            </div>
          </form>
        </CardContent>
      </Card>

      {error ? (
        <div className="rounded-2xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
          Live refresh warning: {error}
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1.1fr,0.9fr]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle>{backlogMode ? "Open analyst backlog" : "Filtered live case stream"}</CardTitle>
              <Badge variant="neutral" className="w-fit">
                DB
              </Badge>
            </div>
            <CardDescription>
              {data.pagination.total} matching cases across {data.pagination.total_pages} page(s).
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            <StatChip
              label={`New in last ${data.live_window.window_seconds}s`}
              value={data.live_window.matching_cases.toString()}
              detail="Matches your current filters"
            />
            <StatChip
              label={`Blocks in last ${data.live_window.window_seconds}s`}
              value={data.live_window.blocked_cases.toString()}
              detail="All BLOCK decisions"
            />
            <StatChip
              label={`Reviews in last ${data.live_window.window_seconds}s`}
              value={data.live_window.review_cases.toString()}
              detail="All REVIEW decisions"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle>Live activity strip</CardTitle>
              <Badge variant="neutral" className="w-fit">
                Recent decisions + feedback
              </Badge>
            </div>
            <CardDescription>
              The strip below is populated from the latest persisted activities, not from hardcoded demo text.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.activities.slice(0, 4).map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-border/70 bg-panelMuted/35 px-4 py-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  {item.decision ? (
                    <DecisionBadge decision={item.decision} />
                  ) : (
                    <Badge variant="neutral" className="w-fit">
                      Feedback
                    </Badge>
                  )}
                  {item.transaction_id ? (
                    <Badge variant="neutral" className="w-fit">
                      {item.transaction_id}
                    </Badge>
                  ) : null}
                </div>
                <p className="mt-3 text-sm font-medium">{item.message}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      {data.items.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-muted">
              The system is live, but no persisted cases match the current filters yet.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle>{backlogMode ? "Open review cases" : "Case list"}</CardTitle>
              <Badge variant="neutral" className="w-fit">
                Auto-refresh in live mode
              </Badge>
            </div>
            <CardDescription>
              New cases rise to the top automatically when live mode is on. Fresh rows glow briefly so arrivals are
              easy to spot during a demo.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.items.map((item) => {
              const recent = recentDecision(item.decision_time, 30);
              const highlighted = (freshRowIds[item.case_id] ?? 0) > Date.now();
              return (
                <Link
                  key={item.case_id}
                  href={`/cases/${item.case_id}`}
                  className={cn(
                    "grid gap-4 rounded-2xl border border-border/70 bg-panelMuted/40 p-4 transition hover:border-accent/30 hover:bg-accent/5 md:grid-cols-[1.2fr,0.7fr,0.7fr,0.7fr,0.8fr,0.8fr,0.8fr]",
                    highlighted && "live-row-fresh border-accent/40 bg-accent/10 shadow-[0_0_0_1px_rgba(79,195,161,0.16)]",
                  )}
                >
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">
                        {item.transaction_id}
                      </p>
                      {recent ? (
                        <Badge variant="low" className="w-fit">
                          New
                        </Badge>
                      ) : null}
                    </div>
                    <p className="mt-2 text-base font-medium">{item.account_id ?? "unknown account"}</p>
                    <p className="text-sm text-muted">{formatScenarioLabel(item.scenario)}</p>
                    <p className="mt-2 text-xs text-muted">
                      {new Date(item.decision_time).toLocaleString()} • {item.status}
                    </p>
                  </div>
                  <Stat label="Decision" value={<DecisionBadge decision={item.decision} />} />
                  <Stat label="Score" value={item.score === null ? "n/a" : item.score.toFixed(3)} />
                  <Stat label="Amount" value={item.amount === null ? "n/a" : item.amount.toFixed(2)} />
                  <Stat label="Geo" value={item.country ?? "n/a"} />
                  <Stat label="Channel" value={item.channel ?? "n/a"} />
                  <Stat label="Status" value={item.status} />
                </Link>
              );
            })}

            <div className="flex items-center justify-between border-t border-border/70 pt-4 text-sm text-muted">
              <p>
                Page {data.pagination.page} of {data.pagination.total_pages}
              </p>
              <div className="flex gap-3">
                {data.pagination.page > 1 ? (
                  <Link
                    className="rounded-xl border border-border px-3 py-2 hover:bg-panelMuted/50"
                    href={`?${buildPageQuery(initialParams, data.pagination.page - 1)}`}
                  >
                    Previous
                  </Link>
                ) : null}
                {data.pagination.page < data.pagination.total_pages ? (
                  <Link
                    className="rounded-xl border border-border px-3 py-2 hover:bg-panelMuted/50"
                    href={`?${buildPageQuery(initialParams, data.pagination.page + 1)}`}
                  >
                    Next
                  </Link>
                ) : null}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
      <div className="text-sm font-medium">{value}</div>
    </div>
  );
}

function StatChip({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-panelMuted/35 px-4 py-4">
      <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
      <p className="mt-3 text-2xl font-semibold">{value}</p>
      <p className="mt-2 text-sm text-muted">{detail}</p>
    </div>
  );
}

function buildLiveQuery(params: {
  page: string;
  search: string;
  status: string;
  decision: string;
  sortOrder: string;
}) {
  const query = new URLSearchParams({
    page: params.page,
    page_size: "20",
    sort_by: "decision_time",
    sort_order: params.sortOrder,
  });
  if (params.status) query.set("status", params.status);
  if (params.decision) query.set("decision", params.decision);
  if (params.search) query.set("search", params.search);
  return query.toString();
}

function buildPageQuery(
  params: {
    page: string;
    search: string;
    status: string;
    decision: string;
    sortOrder: string;
  },
  page: number,
) {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.decision) query.set("decision", params.decision);
  if (params.sortOrder) query.set("sort_order", params.sortOrder);
  query.set("page", page.toString());
  return query.toString();
}
