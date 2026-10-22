import type { PainPointFilters, SourceFilters } from ".";

export const queryKeys = {
  health: ["health"] as const,
  providers: ["providers"] as const,
  taxonomy: ["taxonomy"] as const,
  jobs: (params: object) => ["jobs", params] as const,
  job: (jobId: string) => ["job", jobId] as const,
  jobLogs: (jobId: string, params: object) => ["job-logs", jobId, params] as const,
  painPoints: (filters: PainPointFilters) => ["pain-points", filters] as const,
  painPoint: (painPointId: string) => ["pain-point", painPointId] as const,
  sources: (filters: SourceFilters) => ["sources", filters] as const,
};
