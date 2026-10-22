import type { SelectHTMLAttributes } from "react";

import { cn } from "../../lib/utils";

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-10 w-full rounded-lg border border-line bg-white px-3 text-sm text-ink",
        className,
      )}
      {...props}
    />
  );
}
