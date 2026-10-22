import type { HTMLAttributes } from "react";

import { cn } from "../../lib/utils";

const toneClasses: Record<string, string> = {
  neutral: "bg-slate-100 text-slate-700",
  ok: "bg-emerald-100 text-emerald-800",
  warn: "bg-amber-100 text-amber-900",
  danger: "bg-red-100 text-red-800",
  info: "bg-blue-100 text-blue-800",
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: keyof typeof toneClasses;
}

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        toneClasses[tone],
        className,
      )}
      {...props}
    />
  );
}
