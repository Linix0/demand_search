import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import { listJobs, type Job, type JobStatus } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { PageHeader } from "../../components/page-header";
import { Pagination } from "../../components/pagination";
import { EmptyState, ErrorState, LoadingState } from "../../components/query-state";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Field } from "../../components/ui/field";
import { Select } from "../../components/ui/select";
import { StatusBadge } from "../../components/ui/status-badge";
import { errorMessage } from "../../lib/errors";
import { formatDateTime } from "../../lib/utils";

const statusOptions = [
  { value: "", label: "全部状态" },
  { value: "draft", label: "草稿" },
  { value: "queued", label: "排队中" },
  { value: "running", label: "运行中" },
  { value: "paused", label: "已暂停" },
  { value: "completed", label: "已完成" },
  { value: "completed_with_errors", label: "部分完成" },
  { value: "failed", label: "失败" },
  { value: "cancelled", label: "已取消" },
] as const;

function parsePage(value: string | null): number {
  const parsed = Number(value ?? 1);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export function JobsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parsePage(searchParams.get("page"));
  const status = searchParams.get("status") ?? "";
  const params = {
    page,
    page_size: 20,
    status: (status || undefined) as JobStatus | undefined,
  };
  const jobs = useQuery({ queryKey: queryKeys.jobs(params), queryFn: () => listJobs(params) });

  function setPage(nextPage: number) {
    const next = new URLSearchParams(searchParams);
    if (nextPage <= 1) next.delete("page");
    else next.set("page", String(nextPage));
    setSearchParams(next);
  }

  function setStatus(nextStatus: string) {
    const next = new URLSearchParams(searchParams);
    next.delete("page");
    if (nextStatus) next.set("status", nextStatus);
    else next.delete("status");
    setSearchParams(next);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Research jobs"
        title="研究任务"
        description="任务状态、进度、来源数量和日志均来自持久化记录；页面只请求当前页数据。"
        actions={
          <Link to="/jobs/new">
            <Button>
              <Plus className="size-4" aria-hidden="true" />
              新建研究任务
            </Button>
          </Link>
        }
      />

      <Card>
        <CardContent className="space-y-4">
          <div className="max-w-xs">
            <Field id="job-status-filter" label="状态筛选">
              <Select
                id="job-status-filter"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          {jobs.isLoading ? <LoadingState label="正在加载研究任务…" /> : null}
          {jobs.isError ? <ErrorState message={errorMessage(jobs.error)} /> : null}
          {jobs.data?.items.length === 0 ? (
            <EmptyState
              title="没有匹配的研究任务"
              description="可以新建任务，或先在概览页运行离线演示。"
            />
          ) : null}

          {jobs.data && jobs.data.items.length > 0 ? (
            <div className="overflow-x-auto rounded-xl border border-line">
              <table className="min-w-full divide-y divide-line text-left text-sm">
                <thead className="bg-slate-50 text-xs font-semibold text-muted uppercase">
                  <tr>
                    <th scope="col" className="px-4 py-3">任务</th>
                    <th scope="col" className="px-4 py-3">状态</th>
                    <th scope="col" className="px-4 py-3">进度</th>
                    <th scope="col" className="px-4 py-3">来源 / 候选</th>
                    <th scope="col" className="px-4 py-3">成本</th>
                    <th scope="col" className="px-4 py-3">创建时间</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line bg-white">
                  {jobs.data.items.map((job) => (
                    <JobRow key={job.id} job={job} />
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {jobs.data ? (
            <Pagination
              page={jobs.data.page}
              pageSize={jobs.data.page_size}
              total={jobs.data.total}
              onPageChange={setPage}
              disabled={jobs.isFetching}
            />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function JobRow({ job }: { job: Job }) {
  return (
    <tr className="hover:bg-blue-50/30">
      <td className="px-4 py-3">
        <Link to={`/jobs/${job.id}`} className="font-semibold text-ink hover:text-brand">
          {job.name}
        </Link>
        <p className="mt-1 max-w-xl truncate text-xs text-muted">{job.description || "无描述"}</p>
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={job.status} />
      </td>
      <td className="px-4 py-3">
        <span className="font-semibold text-ink">{job.progress_percent}%</span>
        <span className="ml-2 text-xs text-muted">{job.stage}</span>
      </td>
      <td className="px-4 py-3 text-muted">
        {job.discovered_source_count} / {job.extracted_pain_point_count}
      </td>
      <td className="px-4 py-3 text-muted">
        {String(job.estimated_cost)} / {String(job.cost_limit)}
      </td>
      <td className="px-4 py-3 text-muted">{formatDateTime(job.created_at)}</td>
    </tr>
  );
}
