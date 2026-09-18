"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Activity, ChevronRight, X } from "lucide-react";
import { api } from "@/lib/api";

function StatusBadge({ status }) {
  const styles =
    status === "ok"
      ? "text-success border-success/30 bg-success/10"
      : "text-danger border-danger/30 bg-danger/10";
  return <span className={`rounded-sm border px-2 py-0.5 text-xs ${styles}`}>{status}</span>;
}

export default function TracesPage() {
  const [traces, setTraces] = useState([]);
  const [options, setOptions] = useState(null);
  const [filters, setFilters] = useState({ status: "", llm_model: "", pipeline_id: "", min_latency_ms: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [t, opts] = await Promise.all([api.listTraces(filters), api.getTraceOptions()]);
      setTraces(t);
      setOptions(opts);
      setError(null);
    } catch (e) {
      setError("Couldn't reach the backend. Is it running on :8000?");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function setFilter(key, value) {
    setFilters((f) => ({ ...f, [key]: value }));
  }

  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <div className="mb-8">
        <h1 className="text-lg font-medium text-text">Traces</h1>
        <p className="mt-1 text-sm text-muted">
          Recent Playground requests, with full per-stage timing and token usage for each. No
          Cost column yet — that needs real per-token pricing, which is Phase 12's job.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {options && (
        <div className="mb-4 flex flex-wrap items-end gap-3 rounded-md border border-border bg-surface p-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-muted">Status</span>
            <select
              value={filters.status}
              onChange={(e) => setFilter("status", e.target.value)}
              className="rounded-sm border border-border bg-bg px-2 py-1.5 text-xs text-text focus:border-accent focus:outline-none"
            >
              <option value="">All</option>
              {options.status.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-muted">Model</span>
            <select
              value={filters.llm_model}
              onChange={(e) => setFilter("llm_model", e.target.value)}
              className="rounded-sm border border-border bg-bg px-2 py-1.5 text-xs text-text focus:border-accent focus:outline-none"
            >
              <option value="">All</option>
              {options.llm_model.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-muted">Pipeline</span>
            <select
              value={filters.pipeline_id}
              onChange={(e) => setFilter("pipeline_id", e.target.value)}
              className="rounded-sm border border-border bg-bg px-2 py-1.5 text-xs text-text focus:border-accent focus:outline-none"
            >
              <option value="">All</option>
              {options.pipelines.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-muted">Min Latency (ms)</span>
            <input
              type="number"
              value={filters.min_latency_ms}
              onChange={(e) => setFilter("min_latency_ms", e.target.value)}
              placeholder="e.g. 500"
              className="w-28 rounded-sm border border-border bg-bg px-2 py-1.5 text-xs text-text placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </label>
          {activeFilterCount > 0 && (
            <button
              onClick={() => setFilters({ status: "", llm_model: "", pipeline_id: "", min_latency_ms: "" })}
              className="flex items-center gap-1 text-xs text-muted hover:text-text"
            >
              <X size={12} /> Clear filters
            </button>
          )}
        </div>
      )}

      <div className="overflow-hidden rounded-md border border-border">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-surface text-xs text-muted">
              <th className="px-4 py-2.5 font-normal">Request ID</th>
              <th className="px-4 py-2.5 font-normal">Status</th>
              <th className="px-4 py-2.5 font-normal">Latency</th>
              <th className="px-4 py-2.5 font-normal">Model</th>
              <th className="px-4 py-2.5 font-normal">Pipeline</th>
              <th className="px-4 py-2.5 font-normal">Tokens</th>
              <th className="px-4 py-2.5 font-normal">Time</th>
              <th className="px-4 py-2.5 font-normal"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-muted">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && traces.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-muted">
                  No requests match these filters. Ask something in the Playground to generate one.
                </td>
              </tr>
            )}
            {traces.map((t) => (
              <tr key={t.id} className="border-b border-border last:border-0 hover:bg-surfaceHover">
                <td className="px-4 py-3">
                  <Link href={`/traces/${t.id}`} className="flex items-center gap-1.5 font-mono text-xs text-accent hover:underline">
                    <Activity size={12} />
                    {t.id.slice(0, 8)}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={t.status} />
                </td>
                <td className="px-4 py-3 text-muted">{t.total_latency_ms}ms</td>
                <td className="px-4 py-3 font-mono text-xs text-muted">{t.llm_model || "—"}</td>
                <td className="px-4 py-3 text-muted">{t.pipeline_name || "—"}</td>
                <td className="px-4 py-3 text-muted">{t.total_tokens ?? "—"}</td>
                <td className="px-4 py-3 text-muted">{new Date(t.created_at).toLocaleString()}</td>
                <td className="px-4 py-3 text-right">
                  <Link href={`/traces/${t.id}`}>
                    <ChevronRight size={14} className="text-muted" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}