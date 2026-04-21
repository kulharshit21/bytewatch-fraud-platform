import { Badge } from "@/components/ui/badge";
import { DecisionBadge } from "@/components/status";
import { cn } from "@/lib/utils";
import type { LiveActivity } from "@/lib/live-utils";

export function ActivityToastStack({
  toasts,
}: {
  toasts: Array<LiveActivity & { toastId: string }>;
}) {
  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-[min(360px,calc(100vw-2rem))] flex-col gap-3">
      {toasts.map((toast) => (
        <div
          key={toast.toastId}
          className={cn(
            "rounded-2xl border border-border/80 bg-panel/95 px-4 py-4 shadow-panel backdrop-blur",
            "animate-[toast-slide-in_220ms_ease-out]",
          )}
        >
          <div className="flex flex-wrap items-center gap-2">
            {toast.decision ? (
              <DecisionBadge decision={toast.decision} />
            ) : (
              <Badge variant="neutral" className="w-fit">
                Feedback
              </Badge>
            )}
            {toast.transaction_id ? (
              <Badge variant="neutral" className="w-fit">
                {toast.transaction_id}
              </Badge>
            ) : null}
          </div>
          <p className="mt-3 text-sm font-medium">{toast.message}</p>
        </div>
      ))}
    </div>
  );
}
