import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowRight, CheckCircle2, FlaskConical, ShieldAlert } from "lucide-react";
import { Link, useNavigate } from "react-router";

import { getHealth, getProviders, listJobs, listPainPoints, runDemoJob } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { PageHeader } from "../../components/page-header";
import { ErrorState, LoadingState } from "../../components/query-state";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { StatusBadge } from "../../components/ui/status-badge";
import { errorMessage } from "../../lib/errors";
import { formatDateTime, formatScore } from "../../lib/utils";

export function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const health = useQuery({ queryKey: queryKeys.health, queryFn: getHealth });
  const providers = useQuery({ queryKey: queryKeys.providers, queryFn: getProviders });
  const jobs = useQuery({
    queryKey: queryKeys.jobs({ page: 1, page_size: 5 }),
    queryFn: () => listJobs({ page: 1, page_size: 5 }),
  });
  const painPoints = useQuery({
    queryKey: queryKeys.painPoints({ page: 1, page_size: 5, sort_by: "evidence_score" }),
    queryFn: () =>
      listPainPoints({ page: 1, page_size: 5, sort_by: "evidence_score", sort_order: "desc" }),
  });
  const demo = useMutation({
    mutationFn: runDemoJob,
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["pain-points"] }),
        queryClient.invalidateQueries({ queryKey: ["sources"] }),
      ]);
      navigate(`/jobs/${result.job.id}`);
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Evidence first"
        title="行业痛点证据雷达"
        description="从公开来源的可追溯片段出发，分开计算证据置信度与商业机会分，并在人工核验后形成可导出的研究结论。"
        actions={
          <Button onClick={() => demo.mutate()} disabled={demo.isPending}>
            <FlaskConical className="size-4" aria-hidden="true" />
            {demo.isPending ? "正在运行离线演示…" : "运行离线演示"}
          </Button>
        }
      />

      {demo.isError ? <ErrorState message={errorMessage(demo.error)} /> : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" aria-label="运行概览">
        <MetricCard
          label="服务健康"
          value={health.data ? health.data.status.toUpperCase() : "—"}
          detail={
            health.data
              ? `数据库 ${health.data.checks.database?.status ?? "unknown"} · Redis ${health.data.checks.redis?.status ?? "unknown"}`
              : "正在检查服务状态"
          }
          icon={<Activity className="size-4" aria-hidden="true" />}
        />
        <MetricCard
          label="研究任务"
          value={jobs.data ? String(jobs.data.total) : "—"}
          detail="服务端分页计数"
          icon={<CheckCircle2 className="size-4" aria-hidden="true" />}
        />
        <MetricCard
          label="痛点候选"
          value={painPoints.data ? String(painPoints.data.total) : "—"}
          detail="事实证据与假设分开管理"
          icon={<ShieldAlert className="size-4" aria-hidden="true" />}
        />
        <MetricCard
          label="当前模式"
          value="Mock"
          detail="无需外部密钥即可完成离线闭环"
          icon={<FlaskConical className="size-4" aria-hidden="true" />}
        />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle>最近研究任务</CardTitle>
            <Link to="/jobs" className="inline-flex items-center gap-1 text-sm font-semibold text-brand">
              查看全部 <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </CardHeader>
          <CardContent>
            {jobs.isLoading ? <LoadingState label="正在加载任务…" /> : null}
            {jobs.isError ? <ErrorState message={errorMessage(jobs.error)} /> : null}
            {jobs.data?.items.length === 0 ? (
              <p className="rounded-xl border border-dashed border-line p-6 text-sm text-muted">
                还没有任务。运行离线演示可验证完整证据链路。
              </p>
            ) : null}
            <ul className="divide-y divide-line">
              {jobs.data?.items.map((job) => (
                <li key={job.id} className="py-3 first:pt-0 last:pb-0">
                  <Link to={`/jobs/${job.id}`} className="group flex items-start justify-between gap-4">
                    <span>
                      <span className="block text-sm font-semibold text-ink group-hover:text-brand">
                        {job.name}
                      </span>
                      <span className="mt-1 block text-xs text-muted">
                        {formatDateTime(job.created_at)} · {job.discovered_source_count} 个来源 ·{" "}
                        {job.extracted_pain_point_count} 个候选
                      </span>
                    </span>
                    <span className="flex shrink-0 items-center gap-2">
                      <span className="text-xs font-semibold text-muted">{job.progress_percent}%</span>
                      <StatusBadge status={job.status} />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Provider 状态</CardTitle>
          </CardHeader>
          <CardContent>
            {providers.isLoading ? <LoadingState label="正在读取 Provider…" /> : null}
            {providers.isError ? <ErrorState message={errorMessage(providers.error)} /> : null}
            <ul className="space-y-3">
              {providers.data?.map((provider) => (
                <li key={provider.provider_code} className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-ink">{provider.display_name}</p>
                    <p className="mt-0.5 text-xs leading-5 text-muted">{provider.note}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <StatusBadge status={provider.health_status} />
                    <Badge tone={provider.enabled ? "info" : "neutral"}>
                      {provider.enabled ? "启用" : "禁用"}
                    </Badge>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle>证据分最高的候选</CardTitle>
          <Link
            to="/pain-points"
            className="inline-flex items-center gap-1 text-sm font-semibold text-brand"
          >
            进入工作台 <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </CardHeader>
        <CardContent>
          {painPoints.isLoading ? <LoadingState label="正在加载痛点…" /> : null}
          {painPoints.isError ? <ErrorState message={errorMessage(painPoints.error)} /> : null}
          {painPoints.data?.items.length === 0 ? (
            <p className="text-sm text-muted">暂无痛点候选。运行离线演示后会生成可追溯样例。</p>
          ) : null}
          <div className="grid gap-3 lg:grid-cols-2">
            {painPoints.data?.items.map((item) => (
              <Link
                key={item.id}
                to={`/pain-points/${item.id}`}
                className="rounded-xl border border-line p-4 transition-colors hover:border-blue-300 hover:bg-blue-50/40"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="line-clamp-2 text-sm font-semibold leading-6 text-ink">
                    {item.canonical_statement}
                  </p>
                  <StatusBadge status={item.status} />
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
                  <span>证据 {formatScore(item.evidence_confidence_score)}</span>
                  <span aria-hidden="true">·</span>
                  <span>机会 {formatScore(item.commercial_opportunity_score)}</span>
                  <span aria-hidden="true">·</span>
                  <span>{item.distinct_source_count} 个独立来源</span>
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function MetricCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</p>
          <p className="mt-2 text-2xl font-bold text-ink">{value}</p>
          <p className="mt-1 text-xs leading-5 text-muted">{detail}</p>
        </div>
        <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-blue-50 text-brand">
          {icon}
        </span>
      </CardContent>
    </Card>
  );
}
