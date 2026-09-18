"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, FileText, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

function StatusBadge({ status }) {
  const styles =
    status === "ok"
      ? "text-success border-success/30 bg-success/10"
      : "text-danger border-danger/30 bg-danger/10";
  return <span className={`rounded-sm border px-2 py-0.5 text-xs ${styles}`}>{status}</span>;
}

const SPAN_COLORS = {
  "Retrieval: bm25": "#7C8CF8",
  "Retrieval: dense": "#7C8CF8",
  "Retrieval: hybrid": "#7C8CF8",
  Reranking: "#FBBF6E",
  Generation: "#4ADE80",
};

export default function TraceDetailPage({ params }) {
  const { id } = params;
  const [trace, setTrace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      setTrace(await api.getTrace(id));
      setError(null);
    } catch (e) {
      setError("Couldn't load this trace.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading) return <div className="mx-auto max-w-4xl px-8 py-10 text-sm text-muted">Loading…</div>;
  if (!trace) return <div className="mx-auto max-w-4xl px-8 py-10 text-sm text-danger">{error || "Not found."}</div>;

  const total = trace.total_latency_ms || 1;

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <Link href="/traces" className="mb-4 flex items-center gap-1.5 text-xs text-muted hover:text-text">
        <ArrowLeft size={12} /> All traces
      </Link>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="flex items-center gap-2 font-mono text-lg font-medium text-text">
            {trace.id}
          </h1>
          <p className="mt-1 text-sm text-muted">
            {trace.pipeline_name} · {trace.llm_model} · {new Date(trace.created_at).toLocaleString()}
          </p>
        </div>
        <StatusBadge status={trace.status} />
      </div>

      {trace.status === "error" && trace.error_message && (
        <div className="mb-6 flex items-start gap-2 rounded-md border border-danger/30 bg-danger/10 p-4 text-sm text-danger">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <span>{trace.error_message}</span>
        </div>
      )}

      <div className="mb-6 rounded-md border border-border bg-surface p-4">
        <div className="mb-3 flex items-center justify-between text-xs text-muted">
          <span>Request Timeline</span>
          <span>{trace.total_latency_ms}ms total</span>
        </div>
        <div className="flex flex-col gap-2">
          {trace.spans.map((s, i) => (
            <div key={i}>
              <div className="mb-1 flex justify-between text-xs">
                <span className="text-text">{s.name}</span>
                <span className="text-muted">{s.duration_ms}ms</span>
              </div>
              <div className="h-2 w-full rounded-sm bg-bg">
                <div
                  className="h-2 rounded-sm"
                  style={{
                    marginLeft: `${(s.start_ms / total) * 100}%`,
                    width: `${Math.max((s.duration_ms / total) * 100, 1)}%`,
                    backgroundColor: SPAN_COLORS[s.name] || "#7C8CF8",
                  }}
                />
              </div>
            </div>
          ))}
          {trace.spans.length === 0 && <p className="text-xs text-muted">No spans recorded.</p>}
        </div>
      </div>

      <div className="mb-6 grid grid-cols-3 gap-3">
        <div className="rounded-md border border-border bg-surface p-4">
          <div className="text-xs text-muted">Input Tokens</div>
          <div className="mt-1 text-xl text-text">{trace.input_tokens ?? "—"}</div>
        </div>
        <div className="rounded-md border border-border bg-surface p-4">
          <div className="text-xs text-muted">Output Tokens</div>
          <div className="mt-1 text-xl text-text">{trace.output_tokens ?? "—"}</div>
        </div>
        <div className="rounded-md border border-border bg-surface p-4">
          <div className="text-xs text-muted">Total Tokens</div>
          <div className="mt-1 text-xl text-text">{trace.total_tokens ?? "—"}</div>
        </div>
      </div>

      <div className="mb-6 rounded-md border border-border bg-surface p-4">
        <div className="mb-2 text-xs text-muted">Question (redacted)</div>
        <p className="mb-4 text-sm text-text">{trace.question_redacted}</p>
        <div className="mb-2 text-xs text-muted">Answer (redacted)</div>
        <p className="whitespace-pre-wrap text-sm text-text">{trace.answer_redacted}</p>
      </div>

      <div>
        <div className="mb-2 text-xs text-muted">Retrieved Chunks ({trace.retrieved_chunks.length})</div>
        <div className="flex flex-col gap-2">
          {trace.retrieved_chunks.map((c, i) => (
            <div key={i} className="flex items-center justify-between rounded-md border border-border bg-surface p-3 text-sm">
              <span className="flex items-center gap-1.5 text-text">
                <FileText size={13} className="text-muted" />
                {c.filename} <span className="text-muted">· p.{c.page_number}</span>
              </span>
              <span className="font-mono text-xs text-accent">{c.score.toFixed(3)}</span>
            </div>
          ))}
          {trace.retrieved_chunks.length === 0 && (
            <p className="text-sm text-muted">No chunks were retrieved for this request.</p>
          )}
        </div>
      </div>
    </div>
  );
}