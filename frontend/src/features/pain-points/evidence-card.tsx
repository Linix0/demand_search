import type { Evidence } from "../../api";
import { EvidenceLink } from "../../components/evidence-link";
import { StatusBadge } from "../../components/ui/status-badge";
import { formatDateTime } from "../../lib/utils";

export function EvidenceCard({ evidence, index }: { evidence: Evidence; index: number }) {
  return (
    <article className="rounded-xl border border-line p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-muted">证据 #{index}</span>
          <StatusBadge status={evidence.quote_match_status} />
          <StatusBadge status={evidence.manual_verification_status} />
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
            {evidence.evidence_type}
          </span>
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
            强度 {evidence.evidence_strength_score.toFixed(1)}
          </span>
        </div>
        <EvidenceLink
          url={evidence.source_url_snapshot}
          className="text-sm font-semibold text-brand hover:underline"
        />
      </div>
      <blockquote className="mt-3 border-l-4 border-blue-200 bg-blue-50/60 px-4 py-3 text-sm leading-6 text-ink">
        “{evidence.evidence_quote}”
      </blockquote>
      <dl className="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-2 lg:grid-cols-3">
        <div><dt className="font-semibold text-ink">来源</dt><dd>{evidence.source_name || "未知"}</dd></div>
        <div><dt className="font-semibold text-ink">标题</dt><dd>{evidence.source_title || "未提供"}</dd></div>
        <div><dt className="font-semibold text-ink">完整度</dt><dd>{evidence.content_completeness || "未知"}</dd></div>
        <div><dt className="font-semibold text-ink">发布时间</dt><dd>{formatDateTime(evidence.source_published_at_snapshot)}</dd></div>
        <div><dt className="font-semibold text-ink">采集时间</dt><dd>{formatDateTime(evidence.collected_at_snapshot)}</dd></div>
        <div><dt className="font-semibold text-ink">获取方式</dt><dd>{evidence.retrieval_method || "未知"}</dd></div>
        <div><dt className="font-semibold text-ink">来源层级</dt><dd>{evidence.source_trust_tier || "未知"}</dd></div>
        <div className="sm:col-span-2">
          <dt className="font-semibold text-ink">目标地址</dt>
          <dd className="break-all">
            <EvidenceLink url={evidence.target_url} label={evidence.target_url || "缺失"} />
          </dd>
        </div>
      </dl>
      {evidence.manual_note ? <p className="mt-3 text-xs text-muted">人工备注：{evidence.manual_note}</p> : null}
    </article>
  );
}
