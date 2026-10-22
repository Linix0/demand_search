import { Badge } from "./badge";

const statusLabels: Record<string, string> = {
  draft: "草稿",
  queued: "排队中",
  running: "运行中",
  paused: "已暂停",
  completed: "已完成",
  completed_with_errors: "部分完成",
  failed: "失败",
  cancelled: "已取消",
  candidate: "候选",
  needs_review: "待核验",
  verified: "已核验",
  hypothesis: "假设",
  rejected: "不成立",
  duplicate: "重复",
  archived: "已归档",
  exact_match: "精确命中",
  normalized_match: "规范化命中",
  snippet_only: "仅摘要",
  not_found: "未找到",
  unreviewed: "未人工确认",
  healthy: "健康",
  degraded: "降级",
  disabled: "已禁用",
  unavailable: "不可用",
  unknown: "未知",
  blocked: "已阻断",
  error: "错误",
  ok: "正常",
};

function toneFor(status: string): "neutral" | "ok" | "warn" | "danger" | "info" {
  if (["completed", "verified", "healthy", "ok", "exact_match", "normalized_match"].includes(status)) {
    return "ok";
  }
  if (["failed", "error", "rejected", "blocked", "cancelled"].includes(status)) {
    return "danger";
  }
  if (["running", "queued", "needs_review", "degraded", "snippet_only", "unreviewed"].includes(status)) {
    return "warn";
  }
  if (["draft", "candidate", "hypothesis", "paused", "unknown", "disabled"].includes(status)) {
    return "info";
  }
  return "neutral";
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={toneFor(status)}>{statusLabels[status] ?? status}</Badge>;
}
