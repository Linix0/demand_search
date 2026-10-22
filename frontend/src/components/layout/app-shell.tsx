import {
  Database,
  FileDown,
  LayoutDashboard,
  ListChecks,
  Radar,
  SearchCode,
} from "lucide-react";
import { NavLink, Outlet } from "react-router";

import { cn } from "../../lib/utils";

const navigation = [
  { to: "/", label: "概览", icon: LayoutDashboard, end: true },
  { to: "/jobs", label: "研究任务", icon: ListChecks },
  { to: "/pain-points", label: "痛点工作台", icon: Radar },
  { to: "/sources", label: "来源池", icon: SearchCode },
  { to: "/exports", label: "报告导出", icon: FileDown },
];

export function AppShell() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-white/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center justify-between gap-4">
            <NavLink to="/" className="flex items-center gap-3" aria-label="Industry Pain Radar 首页">
              <span className="grid size-9 place-items-center rounded-xl bg-brand text-white shadow-sm">
                <Radar className="size-5" aria-hidden="true" />
              </span>
              <span>
                <span className="block text-sm font-bold tracking-wide text-ink">
                  INDUSTRY PAIN RADAR
                </span>
                <span className="block text-[11px] text-muted">证据驱动 · 单用户本地工作台</span>
              </span>
            </NavLink>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600 lg:hidden">
              <Database className="size-3" aria-hidden="true" />
              Mock
            </span>
          </div>
          <nav aria-label="主导航" className="flex gap-1 overflow-x-auto pb-1 lg:pb-0">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    cn(
                      "inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-blue-50 text-brand"
                        : "text-muted hover:bg-slate-100 hover:text-ink",
                    )
                  }
                >
                  <Icon className="size-4" aria-hidden="true" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs leading-5 text-muted sm:px-6">
        证据置信度与商业机会分始终独立展示。没有原始来源的人工结论只能作为假设，不能标记为已验证事实。
      </footer>
    </div>
  );
}
