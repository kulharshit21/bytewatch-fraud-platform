import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-[0.24em]",
  {
    variants: {
      variant: {
        neutral: "border-border bg-panelMuted text-muted",
        high: "border-danger/40 bg-danger/10 text-danger",
        medium: "border-warning/40 bg-warning/10 text-warning",
        low: "border-accent/40 bg-accent/10 text-accent",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
