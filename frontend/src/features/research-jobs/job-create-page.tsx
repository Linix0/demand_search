import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Play } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { z } from "zod";

import { createJob, getTaxonomy, runJobAction } from "../../api";
import { queryKeys } from "../../api/query-keys";
import { PageHeader } from "../../components/page-header";
import { ErrorState, LoadingState } from "../../components/query-state";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Field } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { Select } from "../../components/ui/select";
import { Textarea } from "../../components/ui/textarea";
import { errorMessage } from "../../lib/errors";

const formSchema = z
  .object({
    name: z.string().trim().min(2, "任务名称至少 2 个字符。").max(200),
    description: z.string().max(2_000),
    seedKeywords: z.string().trim().min(2, "请至少输入一个关键词。"),
    primaryCategory: z.string().min(1, "请选择分类。"),
    tags: z.string(),
    language: z.enum(["zh-CN", "en"]),
    dateFrom: z.string(),
    dateTo: z.string(),
    maxQueries: z.coerce.number().int().min(1).max(20),
    maxResultsPerQuery: z.coerce.number().int().min(1).max(30),
    maxTotalItems: z.coerce.number().int().min(1).max(200),
    minEvidenceScore: z.coerce.number().int().min(0).max(100),
    startImmediately: z.boolean(),
  })
  .refine(
    (values) => !values.dateFrom || !values.dateTo || values.dateFrom <= values.dateTo,
    { path: ["dateTo"], message: "结束日期不能早于开始日期。" },
  );

type FormValues = z.infer<typeof formSchema>;

function splitValues(value: string): string[] {
  return value
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function JobCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const taxonomy = useQuery({ queryKey: queryKeys.taxonomy, queryFn: getTaxonomy });
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      description: "",
      seedKeywords: "",
      primaryCategory: "enterprise_ops",
      tags: "",
      language: "zh-CN",
      dateFrom: "",
      dateTo: "",
      maxQueries: 10,
      maxResultsPerQuery: 3,
      maxTotalItems: 60,
      minEvidenceScore: 35,
      startImmediately: true,
    },
  });

  useEffect(() => {
    const firstCategory = taxonomy.data?.categories[0]?.code;
    if (firstCategory && !taxonomy.data?.categories.some((item) => item.code === form.getValues("primaryCategory"))) {
      form.setValue("primaryCategory", firstCategory);
    }
    if (firstCategory && form.getValues("primaryCategory") === "") {
      form.setValue("primaryCategory", firstCategory);
    }
  }, [form, taxonomy.data]);

  const create = useMutation({
    mutationFn: async (values: FormValues) => {
      const job = await createJob({
        name: values.name,
        description: values.description,
        date_from: values.dateFrom || null,
        date_to: values.dateTo || null,
        config: {
          seed_keywords: splitValues(values.seedKeywords),
          primary_categories: [values.primaryCategory],
          tags: splitValues(values.tags),
          languages: [values.language],
          source_providers: ["mock"],
          max_queries: values.maxQueries,
          max_results_per_query: values.maxResultsPerQuery,
          max_total_items: values.maxTotalItems,
          max_job_cost: 5,
          min_evidence_score: values.minEvidenceScore,
          dedupe_mode: "balanced",
        },
      });
      if (values.startImmediately) {
        await runJobAction(job.id, "start");
      }
      return job;
    },
    onSuccess: async (job) => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      navigate(`/jobs/${job.id}`);
    },
  });

  const errors = form.formState.errors;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Create job"
        title="新建研究任务"
        description="首期仅启用 Mock Provider。真实来源需要完成条款、凭据、限流与策略确认后才能启用。"
        actions={
          <Link to="/jobs">
            <Button variant="secondary">
              <ArrowLeft className="size-4" aria-hidden="true" />
              返回任务列表
            </Button>
          </Link>
        }
      />

      {taxonomy.isLoading ? <LoadingState label="正在加载分类…" /> : null}
      {taxonomy.isError ? <ErrorState message={errorMessage(taxonomy.error)} /> : null}
      {create.isError ? <ErrorState message={errorMessage(create.error)} /> : null}

      <form onSubmit={form.handleSubmit((values) => create.mutate(values))} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>研究范围</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <Field id="job-name" label="任务名称" required error={errors.name?.message}>
              <Input id="job-name" autoComplete="off" {...form.register("name")} />
            </Field>
            <Field id="job-category" label="主分类" required error={errors.primaryCategory?.message}>
              <Select id="job-category" {...form.register("primaryCategory")}>
                {taxonomy.data?.categories.map((category) => (
                  <option key={category.code} value={category.code}>
                    {category.name} ({category.code})
                  </option>
                ))}
              </Select>
            </Field>
            <Field id="job-description" label="任务描述" className="md:col-span-2">
              <Textarea
                id="job-description"
                placeholder="说明要研究的人群、场景或已知线索。"
                {...form.register("description")}
              />
            </Field>
            <Field
              id="job-keywords"
              label="种子关键词"
              hint="用逗号或换行分隔，最多 5 个；空白项会被忽略。"
              required
              error={errors.seedKeywords?.message}
              className="md:col-span-2"
            >
              <Textarea
                id="job-keywords"
                placeholder="例如：spreadsheet reconciliation, manual reporting"
                {...form.register("seedKeywords")}
              />
            </Field>
            <Field
              id="job-tags"
              label="痛点标签"
              hint="用逗号或换行分隔，标签必须来自数据库配置。"
            >
              <Input id="job-tags" {...form.register("tags")} />
            </Field>
            <Field id="job-language" label="语言">
              <Select id="job-language" {...form.register("language")}>
                <option value="zh-CN">简体中文</option>
                <option value="en">English</option>
              </Select>
            </Field>
            <Field id="job-date-from" label="起始日期">
              <Input id="job-date-from" type="date" {...form.register("dateFrom")} />
            </Field>
            <Field id="job-date-to" label="结束日期" error={errors.dateTo?.message}>
              <Input id="job-date-to" type="date" {...form.register("dateTo")} />
            </Field>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>预算与数量边界</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Field id="job-max-queries" label="最大查询数" error={errors.maxQueries?.message}>
              <Input id="job-max-queries" type="number" min={1} max={20} {...form.register("maxQueries")} />
            </Field>
            <Field id="job-max-results" label="每查询结果数" error={errors.maxResultsPerQuery?.message}>
              <Input
                id="job-max-results"
                type="number"
                min={1}
                max={30}
                {...form.register("maxResultsPerQuery")}
              />
            </Field>
            <Field id="job-max-items" label="最大来源总数" error={errors.maxTotalItems?.message}>
              <Input id="job-max-items" type="number" min={1} max={200} {...form.register("maxTotalItems")} />
            </Field>
            <Field id="job-min-evidence" label="最低证据分" error={errors.minEvidenceScore?.message}>
              <Input
                id="job-min-evidence"
                type="number"
                min={0}
                max={100}
                {...form.register("minEvidenceScore")}
              />
            </Field>
            <div className="sm:col-span-2 lg:col-span-4 rounded-xl bg-slate-50 p-4 text-sm text-muted">
              成本上限固定为 5.00 USD；Mock 任务估算成本为 0。服务端仍会执行数量上限与预算校验。
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <label className="flex items-center gap-2 text-sm font-medium text-ink">
              <input
                type="checkbox"
                className="size-4 rounded border-line text-brand"
                {...form.register("startImmediately")}
              />
              创建后立即启动任务
            </label>
            <Button type="submit" size="lg" disabled={create.isPending || taxonomy.isLoading}>
              <Play className="size-4" aria-hidden="true" />
              {create.isPending ? "正在创建并启动…" : "创建任务"}
            </Button>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
