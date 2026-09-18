"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  LayoutDashboard,
  Database,
  Workflow,
  FlaskConical,
  FileQuestion,
  BarChart3,
  Activity,
  ScrollText,
  ShieldCheck,
  Gauge,
  Settings,
  FlaskRound,
} from "lucide-react";

const NAV = [
  {
    group: "Overview",
    items: [{ label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, status: "live" }],
  },
  {
    group: "RAG",
    items: [
      { label: "Datasets", href: "/datasets", icon: Database, status: "live" },
      { label: "Playground", href: "/playground", icon: FlaskRound, status: "live" },
      { label: "Pipelines", href: "/pipelines", icon: Workflow, status: "live" },
    ],
  },
  {
    group: "Evaluation",
    items: [
      { label: "Datasets", href: "/evaluations/datasets", icon: FileQuestion, status: "live" },
      { label: "Experiments", href: "/experiments", icon: FlaskConical, status: "live" },
      { label: "Metrics", href: "/evaluations", icon: BarChart3, status: "live" },
    ],
  },
  {
    group: "Observability",
    items: [
      { label: "Traces", href: "/traces", icon: Activity, status: "live" },
      { label: "Logs", href: "/logs", icon: ScrollText, status: "live" },
    ],
  },
  {
    group: "Security",
    items: [{ label: "Security Tests", href: "/security", icon: ShieldCheck, status: "soon" }],
  },
  {
    group: "Optimization",
    items: [{ label: "Cost & Cache", href: "/optimization", icon: Gauge, status: "soon" }],
  },
  {
    group: "",
    items: [{ label: "Settings", href: "/settings", icon: Settings, status: "soon" }],
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-border bg-surface">
      <div className="flex items-center gap-2 border-b border-border px-5 py-4">
        <div className="h-2 w-2 rounded-full bg-accent" />
        <span className="font-mono text-sm tracking-tight text-text">ragops</span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {NAV.map((section) => (
          <div key={section.group || "root"} className="mb-5">
            {section.group && (
              <div className="mb-1.5 px-2 text-xs text-muted">{section.group}</div>
            )}
            <div className="flex flex-col gap-0.5">
              {section.items.map((item) => {
                const active = pathname?.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "flex items-center justify-between rounded-sm px-2 py-1.5 text-sm transition-colors",
                      active
                        ? "bg-accentMuted/30 text-text"
                        : "text-muted hover:bg-surfaceHover hover:text-text"
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <Icon size={15} />
                      {item.label}
                    </span>
                    {item.status === "soon" && (
                      <span className="rounded-sm border border-border px-1.5 py-0.5 text-[10px] text-muted">
                        soon
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-border px-5 py-3 text-xs text-muted">
        Phase 0–8 · Production Differentiators
      </div>
    </aside>
  );
}