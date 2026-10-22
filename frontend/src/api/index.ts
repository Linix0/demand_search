import type { components } from "./schema";

import { API_BASE_URL, apiClient, toApiError, unwrap, type Schemas } from "./client";

export type Health = Schemas["HealthResponse"];
export type Provider = Schemas["ProviderStatus"];
export type Job = Schemas["JobRead"];
export type JobStatus = Schemas["JobStatus"];
export type JobLog = Schemas["JobLogRead"];
export type JobCreate = Schemas["JobCreateRequest"];
export type JobAction = Schemas["JobActionResponse"];
export type PainPointSummary = Schemas["PainPointListItem"];
export type PainPoint = Schemas["PainPointDetail"];
export type Evidence = Schemas["EvidenceRead"];
export type Score = Schemas["ScoreRead"];
export type SourceItem = Schemas["SourceRead"];
export type Category = Schemas["CategoryResponse"];
export type Tag = Schemas["TagResponse"];
export type ReviewAction = Schemas["ReviewActionResponse"];
export type ExportFormat = components["schemas"]["ExportRequest"]["format"];

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface PainPointFilters {
  page?: number;
  page_size?: number;
  statuses?: string;
  category?: string;
  job_id?: string;
  min_evidence_score?: number;
  min_commercial_score?: number;
  min_coverage_score?: number;
  has_verified_evidence?: boolean;
  has_payment_signal?: boolean;
  q?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface SourceFilters {
  page?: number;
  page_size?: number;
  job_id?: string;
  provider_code?: string;
  source_domain?: string;
  completeness?: Schemas["ContentCompleteness"];
  q?: string;
}

function cleanParams<T extends object>(params: T): T {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value !== undefined && value !== null),
  ) as T;
}

export async function getHealth(): Promise<Health> {
  const { data, error, response } = await apiClient.GET("/health");
  return unwrap(data, error, response);
}

export async function getProviders(): Promise<Provider[]> {
  const { data, error, response } = await apiClient.GET("/api/v1/settings/providers");
  return unwrap(data, error, response).items;
}

export async function runDemoJob(): Promise<JobAction> {
  const { data, error, response } = await apiClient.POST("/api/v1/research-jobs/demo");
  return unwrap(data, error, response);
}

export async function listJobs(
  params: { page?: number; page_size?: number; status?: Schemas["JobStatus"] } = {},
): Promise<Page<Job>> {
  const { data, error, response } = await apiClient.GET("/api/v1/research-jobs", {
    params: { query: cleanParams(params) },
  });
  return unwrap(data, error, response);
}

export async function getJob(jobId: string): Promise<Job> {
  const { data, error, response } = await apiClient.GET("/api/v1/research-jobs/{job_id}", {
    params: { path: { job_id: jobId } },
  });
  return unwrap(data, error, response);
}

export async function createJob(payload: JobCreate): Promise<Job> {
  const { data, error, response } = await apiClient.POST("/api/v1/research-jobs", {
    body: payload,
  });
  return unwrap(data, error, response);
}

export type JobActionName = "start" | "pause" | "resume" | "cancel" | "retry-failed";

export async function runJobAction(jobId: string, action: JobActionName): Promise<JobAction> {
  const pathsByAction = {
    start: "/api/v1/research-jobs/{job_id}/start",
    pause: "/api/v1/research-jobs/{job_id}/pause",
    resume: "/api/v1/research-jobs/{job_id}/resume",
    cancel: "/api/v1/research-jobs/{job_id}/cancel",
    "retry-failed": "/api/v1/research-jobs/{job_id}/retry-failed",
  } as const;
  const { data, error, response } = await apiClient.POST(pathsByAction[action], {
    params: { path: { job_id: jobId } },
  });
  return unwrap(data, error, response);
}

export async function duplicateJob(jobId: string): Promise<Job> {
  const { data, error, response } = await apiClient.POST(
    "/api/v1/research-jobs/{job_id}/duplicate",
    { params: { path: { job_id: jobId } } },
  );
  return unwrap(data, error, response);
}

export async function listJobLogs(
  jobId: string,
  params: { page?: number; page_size?: number } = {},
): Promise<Page<JobLog>> {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/research-jobs/{job_id}/logs",
    { params: { path: { job_id: jobId }, query: cleanParams(params) } },
  );
  return unwrap(data, error, response);
}

export async function listPainPoints(
  filters: PainPointFilters = {},
): Promise<Page<PainPointSummary> & { coverage_warning?: string | null }> {
  const { data, error, response } = await apiClient.GET("/api/v1/pain-points", {
    params: { query: cleanParams(filters) },
  });
  return unwrap(data, error, response);
}

export async function getPainPoint(painPointId: string): Promise<PainPoint> {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/pain-points/{pain_point_id}",
    { params: { path: { pain_point_id: painPointId } } },
  );
  return unwrap(data, error, response);
}

export async function updatePainPoint(
  painPointId: string,
  payload: Schemas["PainPointPatchRequest"],
): Promise<PainPoint> {
  const { data, error, response } = await apiClient.PATCH(
    "/api/v1/pain-points/{pain_point_id}",
    { params: { path: { pain_point_id: painPointId } }, body: payload },
  );
  return unwrap(data, error, response);
}

export async function verifyPainPoint(painPointId: string, reason: string): Promise<ReviewAction> {
  const { data, error, response } = await apiClient.POST(
    "/api/v1/pain-points/{pain_point_id}/verify",
    { params: { path: { pain_point_id: painPointId } }, body: { reason } },
  );
  return unwrap(data, error, response);
}

export async function rejectPainPoint(painPointId: string, reason: string): Promise<ReviewAction> {
  const { data, error, response } = await apiClient.POST(
    "/api/v1/pain-points/{pain_point_id}/reject",
    { params: { path: { pain_point_id: painPointId } }, body: { reason } },
  );
  return unwrap(data, error, response);
}

export async function mergePainPoint(
  painPointId: string,
  targetPainPointId: string,
  reason: string,
): Promise<ReviewAction> {
  const { data, error, response } = await apiClient.POST(
    "/api/v1/pain-points/{pain_point_id}/merge",
    {
      params: { path: { pain_point_id: painPointId } },
      body: { target_pain_point_id: targetPainPointId, reason },
    },
  );
  return unwrap(data, error, response);
}

export async function rescorePainPoint(painPointId: string): Promise<ReviewAction> {
  const { data, error, response } = await apiClient.POST(
    "/api/v1/pain-points/{pain_point_id}/rescore",
    { params: { path: { pain_point_id: painPointId } } },
  );
  return unwrap(data, error, response);
}

export async function addAnnotation(
  painPointId: string,
  payload: Schemas["AnnotationCreateRequest"],
): Promise<Schemas["AnnotationRead"]> {
  const { data, error, response } = await apiClient.POST(
    "/api/v1/pain-points/{pain_point_id}/annotations",
    { params: { path: { pain_point_id: painPointId } }, body: payload },
  );
  return unwrap(data, error, response);
}

export async function listSources(filters: SourceFilters = {}): Promise<Page<SourceItem>> {
  const { data, error, response } = await apiClient.GET("/api/v1/source-items", {
    params: { query: cleanParams(filters) },
  });
  return unwrap(data, error, response);
}

export async function importSourceUrl(url: string, title = ""): Promise<Schemas["UrlRecheckResponse"]> {
  const { data, error, response } = await apiClient.POST("/api/v1/source-items/import-url", {
    body: { url, title },
  });
  return unwrap(data, error, response);
}

export async function recheckSource(sourceId: string): Promise<Schemas["UrlRecheckResponse"]> {
  const { data, error, response } = await apiClient.POST(
    "/api/v1/source-items/{source_id}/recheck-url",
    { params: { path: { source_id: sourceId } } },
  );
  return unwrap(data, error, response);
}

export async function getTaxonomy(): Promise<{ categories: Category[]; tags: Tag[] }> {
  const [categoriesResponse, tagsResponse] = await Promise.all([
    apiClient.GET("/api/v1/taxonomy/categories"),
    apiClient.GET("/api/v1/taxonomy/tags"),
  ]);
  return {
    categories: unwrap(
      categoriesResponse.data,
      categoriesResponse.error,
      categoriesResponse.response,
    ).items,
    tags: unwrap(tagsResponse.data, tagsResponse.error, tagsResponse.response).items,
  };
}

export async function exportPainPoints(
  format: ExportFormat,
  options: { jobId?: string; status?: string; maxItems?: number } = {},
): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/exports/pain-points`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "*/*" },
    body: JSON.stringify({
      format,
      job_id: options.jobId || null,
      status: options.status || null,
      max_items: options.maxItems ?? 1000,
    }),
  });
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    throw toApiError(body, response);
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  return {
    blob: await response.blob(),
    filename: match?.[1] ?? `pain-points.${format === "markdown" ? "md" : format}`,
  };
}
