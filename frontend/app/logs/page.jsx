"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Search, X } from "lucide-react";
import { api } from "@/lib/api";

const SEVERITY_STYLES = {
  ok: "text-success",
  error: "text-danger",
};

export default function LogsPage() {
  const [logs, setLogs] = useState([]);
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const results = await api.listTraces({ search, status: severity, limit: 100 });
      setLogs(results);
      setError(null);
    } catch (e) {
      setError("Couldn't reach the backend. Is it running on :8000?");
    } finally {
      setLoading(false);
    }
  }, [search, severity]);

  useEffect(() => {
    const t = setTimeout(refresh, 250); // debounce search-as-you-type
    return () => clearTimeout(t);
  }, [refresh]);

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <div className="mb-8">
        <h1 className="text-lg font-medium text-text">Logs</h1>
        <p className="mt-1 text-sm text-muted">
          The same request records as Traces, as a dense searchable log instead of a table to
          browse. "Severity" here is just ok/error derived from request status — there's no
          separate debug/info/warn logging level system underneath.
        </p>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <div className="relative flex-1">
          <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search question/answer text or request ID…"
            className="w-full rounded-sm border border-border bg-surface py-2.5 pl-9 pr-3 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none"
          />
        </div>
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="rounded-sm border border-border bg-surface px-3 py-2.5 text-sm text-text focus:border-accent focus:outline-none"
        >
          <option value="">All severities</option>
          <option value="ok">ok</option>
          <option value="error">error</option>
        </select>
        {(search || severity) && (
          <button
            onClick={() => {
              setSearch("");
              setSeverity("");
            }}
            className="flex items-center gap-1 text-xs text-muted hover:text-text"
          >
            <X size={12} /> Clear
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-md border border-border font-mono text-xs">
        {loading && <div className="px-4 py-8 text-center text-muted">Loading…</div>}
        {!loading && logs.length === 0 && (
          <div className="px-4 py-10 text-center text-muted">No log lines match this search.</div>
        )}
        {logs.map((l) => (
          <Link
            key={l.id}
            href={`/traces/${l.id}`}
            className="flex items-center gap-3 border-b border-border px-3 py-2 last:border-0 hover:bg-surfaceHover"
          >
            <span className="text-muted">{new Date(l.created_at).toISOString()}</span>
            <span className={SEVERITY_STYLES[l.status] || "text-muted"}>{l.status.toUpperCase()}</span>
            <span className="text-accent">{l.id.slice(0, 8)}</span>
            <span className="text-muted">{l.pipeline_name || "—"}</span>
            <span className="text-muted">{l.llm_model || "—"}</span>
            <span className="ml-auto text-muted">{l.total_latency_ms}ms</span>
          </Link>
        ))}
      </div>
    </div>
  );
}