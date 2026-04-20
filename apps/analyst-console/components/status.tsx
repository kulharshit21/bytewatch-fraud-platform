import { Badge } from "@/components/ui/badge";

export function DecisionBadge({ decision }: { decision: string }) {
  const normalized = decision?.toUpperCase?.() ?? "UNKNOWN";
  if (normalized === "BLOCK") {
    return <Badge variant="high">block</Badge>;
  }
  if (normalized === "REVIEW") {
    return <Badge variant="medium">review</Badge>;
  }
  return <Badge variant="low">approve</Badge>;
}
