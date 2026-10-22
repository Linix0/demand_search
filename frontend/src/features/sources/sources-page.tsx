import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw, Search } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router";
import { z } from "zod";

import { importSourceUrl, listSources, recheckSource, type SourceFilters } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { EvidenceLink } from "../../components/evidence-link";
import { PageHeader } from "../../components/page-header";
import { Pagination } from "../../components/pagination";
import { EmptyState, ErrorState, LoadingState } from "../../components/query-state";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Field } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { Select } from "../../components/ui/select";
import { StatusBadge } from "../../components/ui/status-badge";
import { errorMessage } from "../../lib/errors";
import { formatDateTime, isHttpUrl } from "../../lib/utils";

const importSchema = z.object({
  url: z
    .string()
    .trim()
    .url("请输入完整 URL。")
    .refine((value) => isHttpUrl(value), "只允许 HTTP(S) 地址。"),
  title: z.string().max(300),
});

type ImportValues = z.infer<typeof importSchema>;

function parsePage(value: string | null): number {
  const parsed = Number(value ?? 1);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}

export function SourcesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [queryDraft, setQueryDraft] = useState(searchParams.get("q") ?? "");
  const [recheckMessage, setRecheckMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const page = parsePage(searchParams.get("page"));
  const filters: SourceFilters = {
    page,
    page_size: 20,
    job_id: searchParams.get("job_id") ?? undefined,
    provider_code: searchParams.get("provider_code") ?? undefined,
    completeness: (searchParams.get("completeness") as SourceFilters["completeness"]) ?? undefined,
    q: searchParams.get("q") ?? undefined,
  };
  const sources = useQuery({
    queryKey: queryKeys.sources(filters),
    queryFn: () => listSources(filters),
  });
  const importForm = useForm<ImportValues>({
    resolver: zodResolver(importSchema),
    defaultValues: { url: "", title: "" },
  });
  const importMutation = useMutation({
    mutationFn: (values: ImportValues) => importSourceUrl(values.url, values.title),
    onSuccess: async () => {
      importForm.reset();
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
  const recheckMutation = useMutation({
    mutationFn: (sourceId: string) => recheckSource(sourceId),
    onSuccess: async (result) => {
      setRecheckMessage(result.message);
      await queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });

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

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Source pool"
        title="来源池"
        description="原始链接、采集时间、完整度和去重状态由后端持久化。手动导入经过 SSRF、重定向、内容类型和响应大小检查。"
      />

      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle>已采集来源</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <form
                className="md:col-span-1"
                onSubmit={(event) => {
                  event.preventDefault();
                  updateFilter("q", queryDraft.trim());
                }}
              >
                <Field id="source-search" label="搜索标题、摘要或域名">
                  <div className="flex gap-2">
                    <Input
                      id="source-search"
                      value={queryDraft}
                      onChange={(event) => setQueryDraft(event.target.value)}
                    />
                    <Button type="submit" size="icon" variant="secondary" aria-label="搜索来源">
                      <Search className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                </Field>
              </form>
              <Field id="source-provider" label="Provider">
                <Select
                  id="source-provider"
                  value={searchParams.get("provider_code") ?? ""}
                  onChange={(event) => updateFilter("provider_code", event.target.value)}
                >
                  <option value="">全部</option>
                  <option value="mock">Mock Search</option>
                  <option value="manual_url">手动 URL</option>
                </Select>
              </Field>
              <Field id="source-completeness" label="内容完整度">
                <Select
                  id="source-completeness"
                  value={searchParams.get("completeness") ?? ""}
                  onChange={(event) => updateFilter("completeness", event.target.value)}
                >
                  <option value="">全部</option>
                  <option value="full_public_content">完整公开内容</option>
                  <option value="partial_content">部分内容</option>
                  <option value="snippet_only">仅摘要</option>
                  <option value="metadata_only">仅元数据</option>
                </Select>
              </Field>
            </div>

            {searchParams.get("job_id") ? (
              <p className="rounded-xl bg-blue-50 p-3 text-sm text-blue-900">
                当前只显示任务 <code>{searchParams.get("job_id")}</code> 的来源。
                <Link className="ml-2 font-semibold underline" to="/sources">清除任务筛选</Link>
              </p>
            ) : null}
            {recheckMessage ? (
              <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900" role="status">
                {recheckMessage}
              </p>
            ) : null}
            {recheckMutation.isError ? <ErrorState message={errorMessage(recheckMutation.error)} /> : null}
            {sources.isLoading ? <LoadingState label="正在加载来源…" /> : null}
            {sources.isError ? <ErrorState message={errorMessage(sources.error)} /> : null}
            {sources.data?.items.length === 0 ? (
              <EmptyState title="没有匹配的来源" description="调整筛选条件，或手动导入一个公开页面。" />
            ) : null}

            {sources.data && sources.data.items.length > 0 ? (
              <div className="overflow-x-auto rounded-xl border border-line">
                <table className="min-w-full divide-y divide-line text-left text-sm">
                  <thead className="bg-slate-50 text-xs font-semibold text-muted uppercase">
                    <tr>
                      <th scope="col" className="px-4 py-3">来源</th>
                      <th scope="col" className="px-4 py-3">完整度</th>
                      <th scope="col" className="px-4 py-3">可信层级</th>
                      <th scope="col" className="px-4 py-3">时间</th>
                      <th scope="col" className="px-4 py-3">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line bg-white">
                    {sources.data.items.map((source) => (
                      <tr key={source.id} className="align-top hover:bg-blue-50/30">
                        <td className="px-4 py-3">
                          <p className="max-w-md font-semibold text-ink">{source.source_title || "无标题"}</p>
                          <p className="mt-1 text-xs text-muted">{source.source_name} · {source.source_domain}</p>
                          {source.content_excerpt ? (
                            <p className="mt-1 line-clamp-2 max-w-xl text-xs leading-5 text-muted">{source.content_excerpt}</p>
                          ) : null}
                          <EvidenceLink
                            url={source.source_url}
                            label={source.source_url}
                            className="mt-1 block max-w-md truncate text-xs font-semibold text-brand hover:underline"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs font-semibold text-ink">{source.content_completeness}</span>
                          <div className="mt-1 text-xs text-muted">{source.url_status}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs text-muted">{source.source_trust_tier}</span>
                          <div className="mt-1 text-xs text-muted">相关度 {source.relevance_score}</div>
                          {source.is_duplicate ? <StatusBadge status="duplicate" /> : null}
                        </td>
                        <td className="px-4 py-3 text-xs text-muted">
                          <div>发布：{formatDateTime(source.published_at)}</div>
                          <div className="mt-1">采集：{formatDateTime(source.collected_at)}</div>
                        </td>
                        <td className="px-4 py-3">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => recheckMutation.mutate(source.id)}
                            disabled={recheckMutation.isPending}
                          >
                            <RotateCcw className="size-4" aria-hidden="true" />
                            重新检查
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {sources.data ? (
              <Pagination
                page={sources.data.page}
                pageSize={sources.data.page_size}
                total={sources.data.total}
                onPageChange={setPage}
                disabled={sources.isFetching}
              />
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>手动导入公开 URL</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={importForm.handleSubmit((values) => importMutation.mutate(values))}>
              <Field
                id="import-url"
                label="HTTP(S) 地址"
                required
                hint="禁止 localhost、私网、链路本地和云元数据地址。"
                error={importForm.formState.errors.url?.message}
              >
                <Input id="import-url" type="url" placeholder="https://example.com/issues/123" {...importForm.register("url")} />
              </Field>
              <Field id="import-title" label="标题" error={importForm.formState.errors.title?.message}>
                <Input id="import-title" {...importForm.register("title")} />
              </Field>
              <Button type="submit" className="w-full" disabled={importMutation.isPending}>
                抓取并保存来源
              </Button>
              {importMutation.isError ? <ErrorState message={errorMessage(importMutation.error)} /> : null}
              {importMutation.data ? (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
                  <p className="font-semibold">{importMutation.data.message}</p>
                  <p className="mt-1 break-all text-xs">{importMutation.data.source.source_url}</p>
                  <EvidenceLink
                    url={importMutation.data.source.source_url}
                    label="打开导入来源"
                    className="mt-2 inline-flex text-xs font-semibold underline"
                  />
                </div>
              ) : null}
              <div className="rounded-xl bg-slate-50 p-3 text-xs leading-5 text-muted">
                页面可打开不等于允许采集。真实 Provider 仍需确认官方 API、站点条款、robots 规则、认证边界和保留期限。
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
