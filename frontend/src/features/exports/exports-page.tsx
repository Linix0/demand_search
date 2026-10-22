import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { exportPainPoints, listJobs } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { PageHeader } from "../../components/page-header";
import { ErrorState } from "../../components/query-state";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Field } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { Select } from "../../components/ui/select";
import { errorMessage } from "../../lib/errors";

const schema = z.object({
  format: z.enum(["csv", "json", "markdown"]),
  status: z.string(),
  jobId: z.string(),
  maxItems: z.coerce.number().int().min(1).max(5_000),
});

type Values = z.infer<typeof schema>;

const formatOptions = [
  { value: "csv", label: "CSV（电子表格）", icon: FileSpreadsheet },
  { value: "json", label: "JSON（结构化）", icon: FileJson },
  { value: "markdown", label: "Markdown（研究报告）", icon: FileText },
] as const;

export function ExportsPage() {
  const jobs = useQuery({
    queryKey: queryKeys.jobs({ page: 1, page_size: 100 }),
    queryFn: () => listJobs({ page: 1, page_size: 100 }),
  });
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { format: "csv", status: "", jobId: "", maxItems: 1000 },
  });
  const exportMutation = useMutation({
    mutationFn: (values: Values) =>
      exportPainPoints(values.format, {
        jobId: values.jobId.trim() || undefined,
        status: values.status || undefined,
        maxItems: values.maxItems,
      }),
    onSuccess: ({ blob, filename }) => {
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(objectUrl);
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Evidence-preserving export"
        title="报告导出"
        description="CSV、JSON 与 Markdown 都保留来源链接、原始引用、评分版本和采集时间。CSV 单元格会中和公式前缀。"
      />

      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader>
            <CardTitle>导出配置</CardTitle>
          </CardHeader>
          <CardContent>
            {exportMutation.isError ? (
              <ErrorState message={errorMessage(exportMutation.error)} className="mb-4" />
            ) : null}
            {exportMutation.isSuccess ? (
              <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900" role="status">
                已生成下载文件：{exportMutation.data.filename}
              </div>
            ) : null}
            <form
              className="space-y-5"
              onSubmit={form.handleSubmit((values) => exportMutation.mutate(values))}
            >
              <Field id="export-format" label="导出格式" required>
                <Select id="export-format" {...form.register("format")}>
                  {formatOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </Select>
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field id="export-status" label="痛点状态">
                  <Select id="export-status" {...form.register("status")}>
                    <option value="">全部状态</option>
                    <option value="candidate">候选</option>
                    <option value="needs_review">待核验</option>
                    <option value="verified">已核验</option>
                    <option value="hypothesis">假设</option>
                    <option value="rejected">不成立</option>
                  </Select>
                </Field>
                <Field id="export-max-items" label="最大条数" error={form.formState.errors.maxItems?.message}>
                  <Input id="export-max-items" type="number" min={1} max={5000} {...form.register("maxItems")} />
                </Field>
              </div>
              <Field
                id="export-job-id"
                label="研究任务 UUID（可选）"
                hint={jobs.data ? `当前可选 ${jobs.data.total} 个任务；仅导出该任务的结果。` : "仅导出指定任务的结果。"}
              >
                <Input id="export-job-id" list="export-job-options" {...form.register("jobId")} />
              </Field>
              <datalist id="export-job-options">
                {jobs.data?.items.map((job) => (
                  <option key={job.id} value={job.id}>{job.name}</option>
                ))}
              </datalist>
              <Button type="submit" size="lg" disabled={exportMutation.isPending}>
                <Download className="size-4" aria-hidden="true" />
                {exportMutation.isPending ? "正在生成…" : "生成并下载"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>导出内容边界</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm leading-6 text-muted">
            <p>每个痛点包含：陈述、状态、三类独立评分、评分版本、来源链接、证据引用、发布时间、采集时间、完整度、引用命中状态和下一步验证。</p>
            <p>不会导出模型生成的伪来源，也不会把没有证据的假设合并进“已验证事实”。</p>
            <p>CSV 中以 <code>=</code>、<code>+</code>、<code>-</code>、<code>@</code>、制表符或回车开头的内容会被中和，避免公式注入。</p>
            <p>导出文件不包含 API Key、Cookie、Authorization 头或完整页面正文。</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
