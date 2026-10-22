import { AlertTriangle, Inbox, LoaderCircle } from "lucide-react";

import { cn } from "../lib/utils";

export function LoadingState({ label = "正在加载…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 rounded-xl border border-line bg-white p-8 text-sm text-muted">
      <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message, className }: { message: string; className?: string }) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900",
        className,
      )}
      role="alert"
    >
      <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <div>
        <p className="font-semibold">请求失败</p>
        <p className="mt-0.5">{message}</p>
      </div>
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-white/70 p-10 text-center">
      <Inbox className="mx-auto size-7 text-slate-400" aria-hidden="true" />
      <p className="mt-3 font-semibold text-ink">{title}</p>
      {description ? <p className="mt-1 text-sm text-muted">{description}</p> : null}
    </div>
  );
}
