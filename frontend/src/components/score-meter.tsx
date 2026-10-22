import { cn, formatScore } from "../lib/utils";

export function ScoreMeter({
  label,
  value,
  tone = "blue",
  hint,
}: {
  label: string;
  value: number;
  tone?: "blue" | "teal" | "slate";
  hint?: string;
}) {
  const color = { blue: "bg-blue-600", teal: "bg-teal-600", slate: "bg-slate-500" }[tone];
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-xs font-semibold text-muted">{label}</span>
        <span className="text-lg font-bold text-ink">{formatScore(value)}</span>
      </div>
      <div
        className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-100"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        aria-label={label}
      >
        <div
          className={cn("h-full rounded-full", color)}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
      {hint ? <p className="mt-1 text-[11px] leading-4 text-muted">{hint}</p> : null}
    </div>
  );
}
