import type { Score } from "../../api";
import { formatDateTime } from "../../lib/utils";

const dimensionLabels: Record<string, string> = {
  source_traceability: "来源可追溯",
  quote_verifiability: "引用可核验",
  directness: "直接性",
  independent_sources: "独立来源数",
  problem_specificity: "问题具体性",
  workaround_behavior: "工作绕过行为",
  recency: "时效性",
  frequency_or_duration: "频率或持续时间",
  severity: "严重程度",
  willingness_to_pay: "付费意愿",
  existing_spend: "已有支出",
  buyer_clarity: "购买者清晰度",
  reachability: "可触达性",
  alternatives_weakness: "替代方案弱点",
  source_diversity: "来源多样性",
  thread_span: "讨论跨度",
  segment_coverage: "人群覆盖",
};

function dimensionName(code: string): string {
  return dimensionLabels[code] ?? code.replaceAll("_", " ");
}

export function ScoreExplanation({ type, score }: { type: string; score: Score }) {
  const typeLabel = type === "evidence" ? "证据置信度" : type === "commercial" ? "商业机会分" : "覆盖度";
  return (
    <section className="rounded-xl border border-line p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-ink">{typeLabel}</h3>
        <span className="text-lg font-bold text-ink">{score.total_score.toFixed(1)}</span>
      </div>
      <p className="mt-1 text-xs text-muted">{score.scoring_version} · {formatDateTime(score.scored_at)}</p>
      <ul className="mt-3 grid gap-3 sm:grid-cols-2">
        {score.dimension_scores.map((dimension, index) => {
          const code = typeof dimension.code === "string" ? dimension.code : `dimension_${index + 1}`;
          const rawScore = typeof dimension.raw_score === "number" ? dimension.raw_score : 0;
          const weight = typeof dimension.weight === "number" ? dimension.weight : 0;
          const rationale = typeof dimension.rationale === "string" ? dimension.rationale : "";
          return (
            <li key={`${code}-${index}`} className="rounded-lg bg-slate-50 p-3">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="font-semibold text-ink">{dimensionName(code)}</span>
                <span className="text-muted">
                  {rawScore.toFixed(1)} / 5 · 权重 {(weight * 100).toFixed(0)}%
                </span>
              </div>
              {rationale ? <p className="mt-1 text-xs leading-5 text-muted">{rationale}</p> : null}
            </li>
          );
        })}
      </ul>
      {score.rule_adjustments.length > 0 ? (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          确定性规则调整：{score.rule_adjustments.join("；")}
        </div>
      ) : null}
    </section>
  );
}
