import { ConsoleShell } from "@/components/console-shell";
import { Card, CardContent } from "@/components/ui/card";

export default function Loading() {
  return (
    <ConsoleShell
      section="overview"
      title="Loading live fraud operations"
      subtitle="The console is waiting on the API and analytics payload."
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Card key={index}>
            <CardContent className="p-6">
              <div className="h-4 w-24 animate-pulse rounded bg-panelMuted/70" />
              <div className="mt-4 h-8 w-20 animate-pulse rounded bg-panelMuted/70" />
              <div className="mt-4 h-4 w-32 animate-pulse rounded bg-panelMuted/70" />
            </CardContent>
          </Card>
        ))}
      </div>
    </ConsoleShell>
  );
}
