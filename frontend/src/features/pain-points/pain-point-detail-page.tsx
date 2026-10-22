import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, RefreshCcw } from "lucide-react";
import { Link, useParams } from "react-router";

import { getPainPoint, rescorePainPoint, type Score } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { PageHeader } from "../../components/page-header";
import { ErrorState, LoadingState } from "../../components/query-state";
import { ScoreMeter } from "../../components/score-meter";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { StatusBadge } from "../../components/ui/status-badge";
import { errorMessage } from "../../lib/errors";
import { formatDateTime } from "../../lib/utils";
import { AnnotationPanel } from "./annotation-panel";
import { EvidenceCard } from "./evidence-card";
import { MergePanel } from "./merge-panel";
import { ReviewPanel } from "./review-panel";
import { ScoreExplanation } from "./score-explanation";

function latestScores(scores: Score[]): Record<string, Score> {
  return scores.reduce<Record<string, Score>>((result, score) => {
    const previous = result[score.score_type];
    if (!previous || new Date(score.scored_at) > new Date(previous.scored_at)) {
      result[score.score_type] = score;
    }
    return result;
  }, {});
}

export function PainPointDetailPage() {
  const { painPointId = "" } = useParams();
  const queryClient = useQueryClient();
  const detail = useQuery({
    queryKey: queryKeys.painPoint(painPointId),
    queryFn: () => getPainPoint(painPointId),
    enabled: Boolean(painPointId),
  });
  const rescore = useMutation({
    mutationFn: () => rescorePainPoint(painPointId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.painPoint(painPointId) }),
        queryClient.invalidateQueries({ queryKey: ["pain-points"] }),
      ]);
    },
  });

  if (!painPointId) return <ErrorState message="缺少痛点 ID。" />;
  if (detail.isLoading) return <LoadingState label="正在加载痛点详情…" />;
  if (detail.isError) return <ErrorState message={errorMessage(detail.error)} />;
  if (!detail.data) return <ErrorState message="痛点不存在。" />;

  const painPoint = detail.data;
  const scores = latestScores(painPoint.scores);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={`${painPoint.category?.name ?? "未分类"} · ${painPoint.score_version}`}
        title={painPoint.canonical_statement}
        description={`${painPoint.user_segment} · ${painPoint.context}`}
        actions={
          <Link to="/pain-points">
            <Button variant="secondary">
              <ArrowLeft className="size-4" aria-hidden="true" />
              返回工作台
            </Button>
          </Link>
        }
      />

      {rescore.isError ? <ErrorState message={errorMessage(rescore.error)} /> : null}

      <div className="grid gap-6 xl:grid-cols-[1fr_390px]">
        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
              <CardTitle>事实与状态</CardTitle>
              <div className="flex items-center gap-2">
                <StatusBadge status={painPoint.status} />
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => rescore.mutate()}
                  disabled={rescore.isPending}
                >
                  <RefreshCcw className="size-4" aria-hidden="true" />
                  重新计算
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-4 sm:grid-cols-3">
                <ScoreMeter
                  label="证据置信度"
                  value={painPoint.evidence_confidence_score}
                  tone="blue"
                  hint="来源、引用与独立性的可信程度"
                />
                <ScoreMeter
                  label="商业机会分"
                  value={painPoint.commercial_opportunity_score}
                  tone="teal"
                  hint="支付、购买者与替代方案信号"
                />
                <ScoreMeter
                  label="覆盖度"
                  value={painPoint.coverage_score}
                  tone="slate"
                  hint="样本范围提示，不作为事实强度"
                />
              </div>
              <div className="grid gap-3 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-3">
                <SummaryStat label="独立来源" value={painPoint.distinct_source_count} />
                <SummaryStat label="独立讨论串" value={painPoint.distinct_thread_count} />
                <SummaryStat label="证据条目" value={painPoint.evidences.length} />
              </div>
              <DefinitionList
                items={[
                  ["问题详情", painPoint.problem_detail],
                  ["当前绕过方式", painPoint.current_workaround],
                  ["现有方案缺口", painPoint.current_solution_gap],
                  ["付费信号", painPoint.payment_signal_summary || "未观察到"],
                  ["下一步验证", painPoint.validation_next_step || "尚未制定"],
                  ["痛点标签", painPoint.pain_type_tags.join("、") || "无"],
                  ["最近证据时间", formatDateTime(painPoint.last_evidence_at)],
                  ["最近人工复核", formatDateTime(painPoint.last_reviewed_at)],
                ]}
              />
              {painPoint.merged_into_id ? (
                <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                  该痛点已合并到{" "}
                  <Link
                    className="font-semibold underline"
                    to={`/pain-points/${painPoint.merged_into_id}`}
                  >
                    目标痛点
                  </Link>
                  。
                </p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <CardTitle>证据链</CardTitle>
              <span className="text-xs font-semibold text-muted">
                {painPoint.evidences.length} 条持久化证据
              </span>
            </CardHeader>
            <CardContent className="space-y-4">
              {painPoint.evidences.length === 0 ? (
                <p
                  className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900"
                  role="alert"
                >
                  没有持久化证据。该条目不能作为事实结论使用。
                </p>
              ) : null}
              {painPoint.evidences.map((evidence, index) => (
                <EvidenceCard key={evidence.id} evidence={evidence} index={index + 1} />
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>评分历史与解释</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.entries(scores).map(([type, score]) => (
                <ScoreExplanation key={type} type={type} score={score} />
              ))}
              <details className="rounded-xl border border-line p-4">
                <summary className="cursor-pointer text-sm font-semibold text-ink">
                  查看全部 {painPoint.scores.length} 条评分记录
                </summary>
                <ul className="mt-3 space-y-2 text-sm text-muted">
                  {painPoint.scores.map((score) => (
                    <li key={score.id}>
                      {formatDateTime(score.scored_at)} · {score.score_type} ·{" "}
                      {score.total_score.toFixed(1)} · {score.scoring_version}
                    </li>
                  ))}
                </ul>
              </details>
            </CardContent>
          </Card>
        </div>

        <aside className="space-y-6">
          <ReviewPanel painPointId={painPointId} />
          <MergePanel painPointId={painPointId} />
          <AnnotationPanel painPointId={painPointId} />
        </aside>
      </div>
    </div>
  );
}

function SummaryStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <span className="block text-xs font-semibold text-muted">{label}</span>
      <span className="mt-1 block font-semibold text-ink">{value}</span>
    </div>
  );
}

function DefinitionList({ items }: { items: Array<[string, string]> }) {
  return (
    <dl className="grid gap-4 sm:grid-cols-2">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</dt>
          <dd className="mt-1 whitespace-pre-wrap text-sm leading-6 text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
