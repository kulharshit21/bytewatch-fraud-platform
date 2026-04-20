import { ConsoleShell } from "@/components/console-shell";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchJson } from "@/lib/api";

type ModelPayload = {
  model_name: string;
  model_version: string;
  model_alias: string;
  review_threshold: number;
  block_threshold: number;
  run_id?: string | null;
  metrics?: Record<string, number>;
};

export default async function ModelsPage() {
  const model = await fetchJson<ModelPayload>("/models/current");

  return (
    <ConsoleShell
      section="models"
      title="Model registry and runtime thresholds"
      subtitle="The console reads the currently promoted champion metadata from the API and MLflow-backed registry cache."
    >
      {model.error || !model.data ? (
        <EmptyState
          title="No champion model available"
          description={model.error ?? "The model endpoint did not return a registered champion model."}
        />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
          <Card>
            <CardHeader>
              <CardTitle>Champion model</CardTitle>
              <CardDescription>Registry metadata currently loaded into the serving path.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Metric label="Name" value={model.data.model_name} />
              <Metric label="Alias" value={model.data.model_alias} />
              <Metric label="Version" value={model.data.model_version} />
              <Metric label="Run ID" value={model.data.run_id ?? "n/a"} />
              <Metric label="Review Threshold" value={model.data.review_threshold.toFixed(2)} />
              <Metric label="Block Threshold" value={model.data.block_threshold.toFixed(2)} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Offline evaluation metrics</CardTitle>
              <CardDescription>Metrics logged during training and persisted with the model metadata artifact.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {model.data.metrics && Object.keys(model.data.metrics).length > 0 ? (
                Object.entries(model.data.metrics).map(([key, value]) => (
                  <div key={key} className="rounded-2xl border border-border/70 bg-panelMuted/40 p-4">
                    <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">{key}</p>
                    <p className="mt-2 text-sm font-medium">{value.toFixed(4)}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted">No metrics were attached to the current champion metadata yet.</p>
              )}
            </CardContent>
          </Card>
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
