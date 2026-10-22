import type { ReactNode } from "react";

import { cn } from "../../lib/utils";

export interface FieldProps {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  className?: string;
  children: ReactNode;
}

export function Field({ id, label, hint, error, required, className, children }: FieldProps) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
        {required ? <span className="ml-1 text-red-600">*</span> : null}
      </label>
      {children}
      {hint && !error ? <p className="text-xs text-muted">{hint}</p> : null}
      {error ? (
        <p className="text-xs font-medium text-red-700" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
