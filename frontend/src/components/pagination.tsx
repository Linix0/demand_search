import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "./ui/button";

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  disabled = false,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  disabled?: boolean;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  return (
    <nav className="flex flex-wrap items-center justify-between gap-3" aria-label="分页">
      <p className="text-sm text-muted">
        显示 {start}–{end} 条，共 {total} 条
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={disabled || page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label="上一页"
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
          上一页
        </Button>
        <span className="min-w-24 text-center text-sm text-muted">
          第 {page} / {totalPages} 页
        </span>
        <Button
          variant="secondary"
          size="sm"
          disabled={disabled || page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          aria-label="下一页"
        >
          下一页
          <ChevronRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </nav>
  );
}
