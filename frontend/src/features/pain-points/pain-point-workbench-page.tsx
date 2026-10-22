import { useQuery } from "@tanstack/react-query";
import { RotateCcw, Search } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import { getTaxonomy, listPainPoints, type PainPointFilters } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { PageHeader } from "../../components/page-header";
import { Pagination } from "../../components/pagination";
import { EmptyState, ErrorState, LoadingState } from "../../components/query-state";
import { ScoreMeter } from "../../components/score-meter";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Field } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { Select } from "../../components/ui/select";
import { StatusBadge } from "../../components/ui/status-badge";
import { errorMessage } from "../../lib/errors";
import { formatDateTime } from "../../lib/utils";

const statusOptions = [
  { value: "", label: "全部状态" },
  { value: "candidate", label: "候选" },
  { value: "needs_review", label: "待核验" },
  { value: "verified", label: "已核验" },
  { value: "hypothesis", label: "假设" },
  { value: "rejected", label: "不成立" },
  { value: "duplicate", label: "重复" },
  { value: "archived", label: "已归档" },
];

function parsePage(value: string | null): number {
  const parsed = Number(value ?? 1);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

function numberParam(value: string | null): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function PainPointWorkbenchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [queryDraft, setQueryDraft] = useState(searchParams.get("q") ?? "");
  const page = parsePage(searchParams.get("page"));
  const filters: PainPointFilters = {
    page,
    page_size: 20,
    statuses: searchParams.get("statuses") ?? undefined,
    category: searchParams.get("category") ?? undefined,
    job_id: searchParams.get("job_id") ?? undefined,
    q: searchParams.get("q") ?? undefined,
    min_evidence_score: numberParam(searchParams.get("min_evidence_score")),
    min_commercial_score: numberParam(searchParams.get("min_commercial_score")),
    sort_by: searchParams.get("sort_by") ?? "evidence_score",
    sort_order: searchParams.get("sort_order") === "asc" ? "asc" : "desc",
  };
  const painPoints = useQuery({
    queryKey: queryKeys.painPoints(filters),
    queryFn: () => listPainPoints(filters),
  });
  const taxonomy = useQuery({ queryKey: queryKeys.taxonomy, queryFn: getTaxonomy });

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    next.delete("page");
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  }

  function setPage(nextPage: number) {
    const next = new URLSearchParams(searchParams);
    if (nextPage <= 1) next.delete("page");
    else next.set("page", String(nextPage));
    setSearchParams(next);
  }

  function resetFilters() {
    setQueryDraft("");
    const next = new URLSearchParams();
    const jobId = searchParams.get("job_id");
    if (jobId) next.set("job_id", jobId);
    setSearchParams(next);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Review workbench"
        title="痛点工作台"
        description="服务端筛选、排序和分页。证据置信度、商业机会与覆盖度分别显示，不做单一排序总分。"
        actions={<Link to="/jobs/new"><Button>新建研究任务</Button></Link>}
      />

      <Card>
        <CardContent className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <form
              className="xl:col-span-2"
              onSubmit={(event) => {
                event.preventDefault();
                updateFilter("q", queryDraft.trim());
              }}
            >
              <Field id="pain-point-search" label="搜索陈述或上下文">
                <div className="flex gap-2">
                  <Input
                    id="pain-point-search"
                    value={queryDraft}
                    onChange={(event) => setQueryDraft(event.target.value)}
                    placeholder="输入关键词"
                  />
                  <Button type="submit" variant="secondary" size="icon" aria-label="搜索">
                    <Search className="size-4" aria-hidden="true" />
                  </Button>
                </div>
              </Field>
            </form>
            <Field id="pain-point-status" label="状态">
              <Select
                id="pain-point-status"
                value={searchParams.get("statuses") ?? ""}
                onChange={(event) => updateFilter("statuses", event.target.value)}
              >
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </Select>
            </Field>
            <Field id="pain-point-category" label="分类">
              <Select
                id="pain-point-category"
                value={searchParams.get("category") ?? ""}
                onChange={(event) => updateFilter("category", event.target.value)}
              >
                <option value="">全部分类</option>
                {taxonomy.data?.categories.map((category) => (
                  <option key={category.code} value={category.code}>{category.name}</option>
                ))}
              </Select>
            </Field>
            <Field id="pain-point-sort" label="排序字段">
              <Select
                id="pain-point-sort"
                value={searchParams.get("sort_by") ?? "evidence_score"}
                onChange={(event) => updateFilter("sort_by", event.target.value)}
              >
                <option value="evidence_score">证据置信度</option>
                <option value="commercial_score">商业机会分</option>
                <option value="coverage_score">覆盖度</option>
                <option value="created_at">创建时间</option>
                <option value="updated_at">更新时间</option>
                <option value="last_evidence_at">最近证据时间</option>
              </Select>
            </Field>
            <Field id="pain-point-direction" label="排序方向">
              <Select
                id="pain-point-direction"
                value={searchParams.get("sort_order") ?? "desc"}
                onChange={(event) => updateFilter("sort_order", event.target.value)}
              >
                <option value="desc">从高到低 / 从新到旧</option>
                <option value="asc">从低到高 / 从旧到新</option>
              </Select>
            </Field>
            <Field id="pain-point-min-evidence" label="最低证据分">
              <Input
                id="pain-point-min-evidence"
                type="number"
                min={0}
                max={100}
                value={searchParams.get("min_evidence_score") ?? ""}
                onChange={(event) => updateFilter("min_evidence_score", event.target.value)}
              />
            </Field>
            <Field id="pain-point-min-commercial" label="最低机会分">
              <Input
                id="pain-point-min-commercial"
                type="number"
                min={0}
                max={100}
                value={searchParams.get("min_commercial_score") ?? ""}
                onChange={(event) => updateFilter("min_commercial_score", event.target.value)}
              />
            </Field>
            <div className="flex items-end">
              <Button variant="secondary" className="w-full" onClick={resetFilters}>
                <RotateCcw className="size-4" aria-hidden="true" />重置筛选
              </Button>
            </div>
          </div>

          {searchParams.get("job_id") ? (
            <div className="rounded-xl bg-blue-50 p-3 text-sm text-blue-900">
              当前只显示任务 <code>{searchParams.get("job_id")}</code> 的结果。
              <Link className="ml-2 font-semibold underline" to="/pain-points">清除任务筛选</Link>
            </div>
          ) : null}
          {painPoints.data?.coverage_warning ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="status">
              {painPoints.data.coverage_warning}
            </div>
          ) : null}
          {painPoints.isLoading ? <LoadingState label="正在加载痛点…" /> : null}
          {painPoints.isError ? <ErrorState message={errorMessage(painPoints.error)} /> : null}
          {painPoints.data?.items.length === 0 ? (
            <EmptyState title="没有匹配的痛点" description="调整筛选条件，或先运行一个研究任务。" />
          ) : null}

          {painPoints.data && painPoints.data.items.length > 0 ? (
            <div className="grid gap-3">
              {painPoints.data.items.map((item) => (
                <Link
                  key={item.id}
                  to={`/pain-points/${item.id}`}
                  className="rounded-xl border border-line bg-white p-4 transition-colors hover:border-blue-300 hover:bg-blue-50/30"
                >
                  <div className="grid gap-4 lg:grid-cols-[1fr_360px] lg:items-center">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge status={item.status} />
                        {item.category ? (
                          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
                            {item.category.name}
                          </span>
                        ) : null}
                        <span className="text-xs text-muted">更新于 {formatDateTime(item.updated_at)}</span>
                      </div>
                      <h2 className="mt-2 line-clamp-2 text-base font-semibold leading-6 text-ink">
                        {item.canonical_statement}
                      </h2>
                      <p className="mt-1 line-clamp-1 text-sm text-muted">
                        {item.user_segment} · {item.context}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                        <span>{item.distinct_source_count} 个独立来源</span>
                        <span>评分版本 {item.score_version}</span>
                        <span className="line-clamp-1">付费信号：{item.payment_signal_summary || "未观察到"}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <ScoreMeter label="证据置信度" value={item.evidence_confidence_score} tone="blue" />
                      <ScoreMeter label="商业机会" value={item.commercial_opportunity_score} tone="teal" />
                      <ScoreMeter label="覆盖度" value={item.coverage_score} tone="slate" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          ) : null}

          {painPoints.data ? (
            <Pagination
              page={painPoints.data.page}
              pageSize={painPoints.data.page_size}
              total={painPoints.data.total}
              onPageChange={setPage}
              disabled={painPoints.isFetching}
            />
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
