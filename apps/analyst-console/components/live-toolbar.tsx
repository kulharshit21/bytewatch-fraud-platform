"use client";

import { useEffect, useState } from "react";
import { Radio, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelativeAge } from "@/lib/live-utils";

export function LiveToolbar({
  liveMode,
  lastSuccessfulFetchAt,
  onRefresh,
  onToggleLiveMode,
  isRefreshing,
  sources,
}: {
  liveMode: boolean;
  lastSuccessfulFetchAt: string;
  onRefresh: () => void;
  onToggleLiveMode: (next: boolean) => void;
  isRefreshing: boolean;
  sources: string[];
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-3xl border border-border/70 bg-panel/55 px-4 py-4 shadow-panel">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => onToggleLiveMode(!liveMode)}
          className={`flex items-center gap-3 rounded-full border px-4 py-2 text-sm font-medium transition ${
            liveMode
              ? "border-accent/40 bg-accent/10 text-foreground"
              : "border-border bg-panelMuted/45 text-muted"
          }`}
        >
          <span className="relative flex h-3 w-3">
            <span
              className={`absolute inline-flex h-full w-full rounded-full ${
                liveMode ? "animate-ping bg-accent/70" : "bg-muted/60"
              }`}
            />
            <span
              className={`relative inline-flex h-3 w-3 rounded-full ${
                liveMode ? "bg-accent" : "bg-muted"
              }`}
            />
          </span>
          {liveMode ? "Live mode on" : "Live mode off"}
        </button>
        <Badge variant="neutral" className="w-fit">
          <Radio className="mr-2 h-3 w-3" />
          {formatRelativeAge(lastSuccessfulFetchAt, now)}
        </Badge>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {sources.map((source) => (
          <Badge key={source} variant="neutral" className="w-fit">
            {source}
          </Badge>
        ))}
        <Button
          type="button"
          variant="secondary"
          className="gap-2"
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          {isRefreshing ? "Syncing" : "Refresh"}
        </Button>
      </div>
    </div>
  );
}
