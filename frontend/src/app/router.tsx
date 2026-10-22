import { Route, Routes } from "react-router";

import { AppShell } from "../components/layout/app-shell";
import { DashboardPage } from "../features/dashboard/dashboard-page";
import { ExportsPage } from "../features/exports/exports-page";
import { JobCreatePage } from "../features/research-jobs/job-create-page";
import { JobDetailPage } from "../features/research-jobs/job-detail-page";
import { JobsPage } from "../features/research-jobs/jobs-page";
import { NotFoundPage } from "../features/not-found-page";
import { PainPointDetailPage } from "../features/pain-points/pain-point-detail-page";
import { PainPointWorkbenchPage } from "../features/pain-points/pain-point-workbench-page";
import { SourcesPage } from "../features/sources/sources-page";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="jobs/new" element={<JobCreatePage />} />
        <Route path="jobs/:jobId" element={<JobDetailPage />} />
        <Route path="pain-points" element={<PainPointWorkbenchPage />} />
        <Route path="pain-points/:painPointId" element={<PainPointDetailPage />} />
        <Route path="sources" element={<SourcesPage />} />
        <Route path="exports" element={<ExportsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
