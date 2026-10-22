import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Copy, Pause, Play, RefreshCcw, RotateCcw, XCircle } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { duplicateJob, getJob, listJobLogs, runJobAction, type JobActionName } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { PageHeader } from "../../components/page-header";
import { Pagination } from "../../components/pagination";
import { ErrorState, LoadingState } from "../../components/query-state";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { StatusBadge } from "../../components/ui/status-badge";
import { errorMessage } from "../../lib/errors";
import { formatDateTime } from "../../lib/utils";

const actionLabels: Record<JobActionName, string> = {
  start: "启动",
  pause: "暂停",
  resume: "继续",
  cancel: "取消",
  "retry-failed": "重试失败项",
};

export function JobDetailPage() {
  const { jobId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [logPage, setLogPage] = useState(1);
  const job = useQuery({
    queryKey: queryKeys.job(jobId),
    queryFn: () => getJob(jobId),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" || status === "queued" ? 2_000 : false;
    },
  });
  const logs = useQuery({
    queryKey: queryKeys.jobLogs(jobId, { page: logPage, page_size: 50 }),
    queryFn: () => listJobLogs(jobId, { page: logPage, page_size: 50 }),
    enabled: Boolean(jobId),
    refetchInterval: job.data?.status === "running" ? 2_000 : false,
  });
  const action = useMutation({
    mutationFn: (name: JobActionName) => runJobAction(jobId, name),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.job(jobId) }),
        queryClient.invalidateQueries({ queryKey: ["job-logs", jobId] }),
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
      ]);
    },
  });
  const duplicate = useMutation({
    mutationFn: () => duplicateJob(jobId),
    onSuccess: async (copy) => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      navigate(`/jobs/${copy.id}`);
    },
  });

  if (!jobId) {
    return <ErrorState message="缺少任务 ID。" />;
  }
  if (job.isLoading) {
    return <LoadingState label="正在加载任务详情…" />;
  }
  if (job.isError) {
    return <ErrorState message={errorMessage(job.error)} />;
  }
  if (!job.data) {
    return <ErrorState message="任务不存在。" />;
  }

  const data = job.data;
  const canStart = ["draft", "failed"].includes(data.status);
  const canPause = ["queued", "running"].includes(data.status);
  const canResume = data.status === "paused";
  const canCancel = !["completed", "cancelled", "completed_with_errors"].includes(data.status);
  const canRetry = data.status === "failed" || data.status === "completed_with_errors";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Job detail"
        title={data.name}
        description={data.description || "无任务描述"}
        actions={
          <>
            <Link to="/jobs">
              <Button variant="secondary">
                <ArrowLeft className="size-4" aria-hidden="true" />
                返回列表
              </Button>
            </Link>
            <Button variant="secondary" onClick={() => duplicate.mutate()} disabled={duplicate.isPending}>
              <Copy className="size-4" aria-hidden="true" />
              复制任务
            </Button>
          </>
        }
      />

      {action.isError ? <ErrorState message={errorMessage(action.error)} /> : null}
      {duplicate.isError ? <ErrorState message={errorMessage(duplicate.error)} /> : null}

      <Card>
        <CardContent className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={data.status} />
            <span className="text-sm text-muted">阶段：{data.stage}</span>
            <span className="text-sm text-muted">进度：{data.progress_percent}%</span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-slate-100"
            role="progressbar"
            aria-valuenow={data.progress_percent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="任务进度"
          >
            <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${data.progress_percent}%` }} />
          </div>
          <div className="flex flex-wrap gap-2">
            {canStart ? <ActionButton name="start" pending={action.isPending} onRun={action.mutate} /> : null}
            {canPause ? <ActionButton name="pause" pending={action.isPending} onRun={action.mutate} /> : null}
            {canResume ? <ActionButton name="resume" pending={action.isPending} onRun={action.mutate} /> : null}
            {canRetry ? <ActionButton name="retry-failed" pending={action.isPending} onRun={action.mutate} /> : null}
            {canCancel ? (
              <Button
                variant="danger"
                size="sm"
                disabled={action.isPending}
                onClick={() => action.mutate("cancel")}
              >
                <XCircle className="size-4" aria-hidden="true" />
                {actionLabels.cancel}
              </Button>
            ) : null}
          </div>
          {data.error_summary ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900" role="alert">
              {data.error_summary}
            </div>
          ) : null}
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="发现来源" value={data.discovered_source_count} />
            <Stat label="处理来源" value={data.processed_source_count} />
            <Stat label="候选痛点" value={data.extracted_pain_point_count} />
            <Stat label="已核验证据" value={data.verified_evidence_count} />
            <Stat label="查询进度" value={`${data.processed_query_count} / ${data.planned_query_count}`} />
            <Stat label="估算成本" value={`${String(data.estimated_cost)} USD`} />
            <Stat label="开始时间" value={formatDateTime(data.started_at)} />
            <Stat label="结束时间" value={formatDateTime(data.finished_at)} />
          </dl>
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <CardTitle>任务日志</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {logs.isLoading ? <LoadingState label="正在加载日志…" /> : null}
            {logs.isError ? <ErrorState message={errorMessage(logs.error)} /> : null}
            {logs.data?.items.length === 0 ? <p className="text-sm text-muted">暂无日志。</p> : null}
            <ol className="space-y-3">
              {logs.data?.items.map((log) => (
                <li key={log.id} className="rounded-xl border border-line p-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                    <span className="font-semibold text-ink">{log.stage}</span>
                    <StatusBadge status={log.level === "error" ? "error" : log.level} />
                    <span>{formatDateTime(log.created_at)}</span>
                  </div>
                  <p className="mt-1.5 text-sm leading-6 text-ink">{log.message}</p>
                </li>
              ))}
            </ol>
            {logs.data ? (
              <Pagination
                page={logs.data.page}
                pageSize={logs.data.page_size}
                total={logs.data.total}
                onPageChange={setLogPage}
                disabled={logs.isFetching}
              />
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>下一步</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <p className="leading-6 text-muted">
              任务完成后进入痛点工作台，逐条打开来源、核对引用，再进行人工核验或合并。
            </p>
            <Link to={`/pain-points?job_id=${data.id}`}>
              <Button className="w-full">查看此任务的痛点</Button>
            </Link>
            <Link to={`/sources?job_id=${data.id}`}>
              <Button variant="secondary" className="w-full">查看来源池</Button>
            </Link>
            <div className="rounded-xl bg-slate-50 p-3 text-xs leading-5 text-muted">
              Provider 失败不会抹掉已持久化证据。重复执行使用持久化状态进行原子认领，不重复消费同一队列消息。
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ActionButton({
  name,
  pending,
  onRun,
}: {
  name: JobActionName;
  pending: boolean;
  onRun: (name: JobActionName) => void;
}) {
  const icons = {
    start: Play,
    pause: Pause,
    resume: RotateCcw,
    cancel: XCircle,
    "retry-failed": RefreshCcw,
  };
  const Icon = icons[name];
  return (
    <Button variant={name === "cancel" ? "danger" : "secondary"} size="sm" disabled={pending} onClick={() => onRun(name)}>
      <Icon className="size-4" aria-hidden="true" />
      {actionLabels[name]}
    </Button>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-ink">{value}</dd>
    </div>
  );
}
