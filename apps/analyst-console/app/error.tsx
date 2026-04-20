"use client";

import { useEffect } from "react";

import { ConsoleShell } from "@/components/console-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <ConsoleShell
      section="overview"
      title="Console error"
      subtitle="A route-level error interrupted the page render. The console is still connected to the real backend, but this specific view needs a retry."
    >
      <Card>
        <CardHeader>
          <CardTitle>Render failure</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted">{error.message}</p>
          <button
            onClick={() => reset()}
            className="rounded-2xl bg-accent px-4 py-3 text-sm font-medium text-background"
          >
            Retry
          </button>
        </CardContent>
      </Card>
    </ConsoleShell>
  );
}
