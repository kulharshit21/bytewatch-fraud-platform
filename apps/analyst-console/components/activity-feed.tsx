import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DecisionBadge } from "@/components/status";
import { formatRelativeAge, type LiveActivity } from "@/lib/live-utils";

export function ActivityFeed({
  title,
  description,
  activities,
  emptyText,
}: {
  title: string;
  description: string;
  activities: LiveActivity[];
  emptyText: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {activities.length === 0 ? (
          <p className="text-sm text-muted">{emptyText}</p>
        ) : (
          activities.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-border/70 bg-panelMuted/35 p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                {item.decision ? (
                  <DecisionBadge decision={item.decision} />
                ) : (
                  <Badge variant="neutral" className="w-fit">
                    Feedback
                  </Badge>
                )}
                {item.score !== undefined && item.score !== null ? (
                  <Badge variant="neutral" className="w-fit">
                    score {item.score.toFixed(2)}
                  </Badge>
                ) : null}
                {item.rule_id ? (
                  <Badge variant="neutral" className="w-fit">
                    {item.rule_id}
                  </Badge>
                ) : null}
              </div>
              <p className="mt-3 text-sm font-medium">{item.message}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                {item.transaction_id ? <span>{item.transaction_id}</span> : null}
                <span>{formatRelativeAge(item.timestamp)}</span>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
