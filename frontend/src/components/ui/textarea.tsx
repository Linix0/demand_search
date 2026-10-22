import type { TextareaHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-24 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink placeholder:text-slate-400",
        className,
      )}
      {...props}
    />
  );
}
