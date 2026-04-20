import { submitFeedback } from "@/app/cases/[caseId]/actions";
import { ConsoleShell } from "@/components/console-shell";
import { EmptyState } from "@/components/empty-state";
import { DecisionBadge } from "@/components/status";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchJson } from "@/lib/api";

type CaseDetail = {
  case_id: string;
  decision: string;
  status: string;
  transaction_id: string;
  model_metadata: {
    model_name: string;
    model_version: string;
    model_alias: string;
    review_threshold: number;
    block_threshold: number;
  };
  rule_hits: Array<{ rule_id: string; explanation: string; severity: string }>;
  raw_transaction: Record<string, unknown>;
  score: number | null;
  reason_codes: Array<{ code: string; description: string; value?: string | number | boolean | null }>;
  features: Record<string, number>;
  feedback: Array<{
    feedback_id: string;
    analyst_id: string;
    feedback_label: string;
    notes: string | null;
    created_at: string;
  }>;
  timeline: Array<{ type: string; timestamp: string; detail: string }>;
};

export default async function CaseDetailPage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  const payload = await fetchJson<CaseDetail>(`/cases/${caseId}`);

  return (
    <ConsoleShell
      section="cases"
      title="Case investigation"
      subtitle="Detailed analyst view of the persisted transaction, the hybrid decision, and the feedback timeline."
    >
      {payload.error || !payload.data ? (
        <EmptyState title="Case unavailable" description={payload.error ?? "No case payload returned."} />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1.35fr,0.9fr]">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>{payload.data.transaction_id}</CardTitle>
                <CardDescription>Primary transaction and decision context.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <Detail label="Decision" value={<DecisionBadge decision={payload.data.decision} />} />
                <Detail label="Status" value={payload.data.status} />
                <Detail label="Score" value={payload.data.score === null ? "n/a" : payload.data.score.toFixed(3)} />
                <Detail label="Amount" value={String(payload.data.raw_transaction.amount ?? "n/a")} />
                <Detail label="Country" value={String(payload.data.raw_transaction.country ?? "n/a")} />
                <Detail label="Channel" value={String(payload.data.raw_transaction.channel ?? "n/a")} />
                <Detail label="Device" value={String(payload.data.raw_transaction.device_id ?? "n/a")} />
                <Detail label="Merchant" value={String(payload.data.raw_transaction.merchant_id ?? "n/a")} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Reason codes and rule hits</CardTitle>
                <CardDescription>Human-readable explanation artifacts returned by the scoring runtime.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <div className="space-y-3">
                  {payload.data.reason_codes.length === 0 ? (
                    <p className="text-sm text-muted">No reason codes were attached.</p>
                  ) : (
                    payload.data.reason_codes.map((item) => (
                      <div key={item.code} className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                        <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">{item.code}</p>
                        <p className="mt-2 text-sm font-medium">{item.description}</p>
                      </div>
                    ))
                  )}
                </div>
                <div className="space-y-3">
                  {payload.data.rule_hits.length === 0 ? (
                    <p className="text-sm text-muted">No deterministic rules fired for this case.</p>
                  ) : (
                    payload.data.rule_hits.map((item) => (
                      <div key={item.rule_id} className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                        <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">{item.rule_id}</p>
                        <p className="mt-2 text-sm font-medium">{item.explanation}</p>
                        <p className="mt-2 text-xs uppercase tracking-[0.24em] text-warning">{item.severity}</p>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Feature snapshot</CardTitle>
                <CardDescription>Online features persisted with the scored transaction.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2">
                {Object.entries(payload.data.features).length === 0 ? (
                  <p className="text-sm text-muted">No features were recorded.</p>
                ) : (
                  Object.entries(payload.data.features).map(([key, value]) => (
                    <div key={key} className="rounded-2xl border border-border/70 bg-panelMuted/35 px-4 py-3">
                      <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">{key}</p>
                      <p className="mt-2 text-sm font-medium">{Number(value).toFixed(3)}</p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Analyst actions</CardTitle>
                <CardDescription>Feedback writes to PostgreSQL and publishes to the feedback topic.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <form action={submitFeedback.bind(null, caseId, "fraud")} className="space-y-3">
                  <input type="hidden" name="analystId" value="analyst_demo" />
                  <textarea
                    name="notes"
                    className="min-h-24 w-full rounded-2xl border border-border bg-panelMuted/40 px-4 py-3 text-sm outline-none transition focus:border-accent/40"
                    placeholder="Notes for fraud investigation"
                  />
                  <button className="w-full rounded-2xl bg-danger px-4 py-3 text-sm font-medium text-white">Mark Fraud</button>
                </form>
                <form action={submitFeedback.bind(null, caseId, "false_positive")} className="space-y-3">
                  <input type="hidden" name="analystId" value="analyst_demo" />
                  <button className="w-full rounded-2xl border border-border bg-panelMuted/50 px-4 py-3 text-sm font-medium hover:bg-panelMuted/80">
                    Mark False Positive
                  </button>
                </form>
                <form action={submitFeedback.bind(null, caseId, "legitimate")} className="space-y-3">
                  <input type="hidden" name="analystId" value="analyst_demo" />
                  <button className="w-full rounded-2xl border border-border bg-panelMuted/50 px-4 py-3 text-sm font-medium hover:bg-panelMuted/80">
                    Mark Legitimate
                  </button>
                </form>
                <form action={submitFeedback.bind(null, caseId, "review")} className="space-y-3">
                  <input type="hidden" name="analystId" value="analyst_demo" />
                  <button className="w-full rounded-2xl bg-warning px-4 py-3 text-sm font-medium text-background">
                    Keep In Review
                  </button>
                </form>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Timeline</CardTitle>
                <CardDescription>Persisted transaction, scoring, and analyst events in sequence.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {payload.data.timeline.map((item) => (
                  <div key={`${item.type}-${item.timestamp}`} className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                    <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">{item.type}</p>
                    <p className="mt-2 text-sm font-medium">{item.detail}</p>
                    <p className="mt-2 text-xs text-muted">{new Date(item.timestamp).toLocaleString()}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Feedback history</CardTitle>
                <CardDescription>Previous analyst actions for this case.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {payload.data.feedback.length === 0 ? (
                  <p className="text-sm text-muted">No analyst feedback has been logged yet.</p>
                ) : (
                  payload.data.feedback.map((item) => (
                    <div key={item.feedback_id} className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                      <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">{item.feedback_label}</p>
                      <p className="mt-2 text-sm font-medium">{item.analyst_id}</p>
                      <p className="mt-2 text-sm text-muted">{item.notes ?? "No notes provided."}</p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </ConsoleShell>
  );
}

function Detail({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-panelMuted/35 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
      <div className="mt-2 text-sm font-medium">{value}</div>
    </div>
  );
}
