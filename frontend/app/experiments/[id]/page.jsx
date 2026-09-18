"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowUp, ArrowDown, Loader2, Download, Star, FlaskConical } from "lucide-react";
import { api } from "@/lib/api";

const METRIC_LABELS = {
  recall_at_k: "Recall@K",
  precision_at_k: "Precision@K",
  hit_rate: "Hit Rate",
  mrr: "MRR",
  ndcg_at_k: "nDCG@K",
  answer_correctness: "Correctness",
  answer_relevance: "Answer Rel.",
  context_relevance: "Context Rel.",
  faithfulness: "Faithfulness",
  hallucination_rate: "Hallucination",
  citation_correctness: "Citation Prec.",
  citation_completeness: "Citation Recall",
  latency_ms: "Latency",
};

const DEFAULT_VISIBLE_METRICS = [
  "answer_correctness",
  "faithfulness",
  "recall_at_k",
  "mrr",
  "hallucination_rate",
  "latency_ms",
];

const DIMENSION_FILTERS = ["chunking_strategy", "embedding_model", "retriever_type", "reranker_type", "llm_model"];
const DIMENSION_LABELS = {
  chunking_strategy: "Chunking",
  embedding_model: "Embedding",
  retriever_type: "Retriever",
  reranker_type: "Reranker",
  llm_model: "LLM",
};

function formatMetric(key, val) {
  if (val === null || val === undefined) return "—";
  if (key === "latency_ms") return `${val.toFixed(0)}ms`;
  return `${(val * 100).toFixed(1)}%`;
}

export default function ExperimentDetailPage({ params }) {
  const { id } = params;

  const [experiment, setExperiment] = useState(null);
  const [directions, setDirections] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [visibleMetrics, setVisibleMetrics] = useState(DEFAULT_VISIBLE_METRICS);
  const [filters, setFilters] = useState({});
  const [sort, setSort] = useState({ key: "composite_score", direction: "desc" });

  const refresh = useCallback(async () => {
    try {
      const [detail, options] = await Promise.all([api.getExperiment(id), api.getExperimentOptions()]);
      setExperiment(detail);
      setDirections(options.metric_directions || {});
      setError(null);
    } catch (e) {
      setError("Couldn't reach the backend. Is it running on :8000?");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!experiment || experiment.status === "completed" || experiment.status === "failed") return;
    const interval = setInterval(refresh, 1500);
    return () => clearInterval(interval);
  }, [experiment, refresh]);

  function toggleMetric(key) {
    setVisibleMetrics((m) => (m.includes(key) ? m.filter((k) => k !== key) : [...m, key]));
  }

  function setFilter(dim, value) {
    setFilters((f) => ({ ...f, [dim]: value }));
  }

  function handleSort(key, isMetric) {
    setSort((s) => {
      if (s.key === key) return { key, direction: s.direction === "asc" ? "desc" : "asc" };
      // first click on a metric defaults to "best first" given that metric's direction
      const defaultDesc = !isMetric || directions[key] !== "lower";
      return { key, direction: defaultDesc ? "desc" : "asc" };
    });
  }

  const filteredSortedRuns = useMemo(() => {
    if (!experiment) return [];
    let runs = experiment.runs.filter((run) => {
      if (!run.config) return true;
      return DIMENSION_FILTERS.every((dim) => !filters[dim] || run.config[dim] === filters[dim]);
    });

    runs = [...runs].sort((a, b) => {
      const getVal = (r) =>
        sort.key === "composite_score" ? r.composite_score : r.summary_metrics?.[sort.key];
      const av = getVal(a);
      const bv = getVal(b);
      if (av === null || av === undefined) return 1; // nulls always sort last
      if (bv === null || bv === undefined) return -1;
      return sort.direction === "asc" ? av - bv : bv - av;
    });

    return runs;
  }, [experiment, filters, sort]);

  if (loading) {
    return <div className="mx-auto max-w-6xl px-8 py-10 text-sm text-muted">Loading…</div>;
  }
  if (!experiment) {
    return <div className="mx-auto max-w-6xl px-8 py-10 text-sm text-danger">{error || "Not found."}</div>;
  }

  const inProgress = experiment.status === "running" || experiment.status === "pending";

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <Link href="/experiments" className="mb-4 flex items-center gap-1.5 text-xs text-muted hover:text-text">
        <ArrowLeft size={12} /> All experiments
      </Link>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-lg font-medium text-text">
            <FlaskConical size={16} className="text-accent" />
            {experiment.name}
          </h1>
          <p className="mt-1 text-sm text-muted">
            {experiment.dataset_name} ·{" "}
            {inProgress ? (
              <span className="inline-flex items-center gap-1 text-warning">
                <Loader2 size={11} className="animate-spin" />
                {experiment.completed_configs}/{experiment.total_configs} completed
              </span>
            ) : (
              <span className={experiment.status === "completed" ? "text-success" : "text-danger"}>
                {experiment.status} — {experiment.completed_configs}/{experiment.total_configs}
              </span>
            )}
          </p>
        </div>
        <a
          href={api.experimentExportUrl(id)}
          download
          className="flex items-center gap-2 rounded-sm border border-border bg-surface px-3 py-2 text-sm text-muted transition-colors hover:text-text"
        >
          <Download size={14} /> Export CSV
        </a>
      </div>

      {error && (
        <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-md border border-border bg-surface p-4">
        {DIMENSION_FILTERS.map((dim) => {
          const values = [...new Set(experiment.runs.map((r) => r.config?.[dim]).filter(Boolean))];
          if (values.length <= 1) return null;
          return (
            <label key={dim} className="flex flex-col gap-1.5">
              <span className="text-xs text-muted">{DIMENSION_LABELS[dim]}</span>
              <select
                value={filters[dim] || ""}
                onChange={(e) => setFilter(dim, e.target.value)}
                className="rounded-sm border border-border bg-bg px-2 py-1.5 text-xs text-text focus:border-accent focus:outline-none"
              >
                <option value="">All</option>
                {values.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
          );
        })}

        <div className="ml-auto flex flex-col gap-1.5">
          <span className="text-xs text-muted">Metrics shown</span>
          <div className="flex flex-wrap gap-1.5">
            {Object.keys(METRIC_LABELS).map((key) => (
              <button
                key={key}
                onClick={() => toggleMetric(key)}
                className={`rounded-sm border px-2 py-1 text-[11px] transition-colors ${
                  visibleMetrics.includes(key)
                    ? "border-accent bg-accent/10 text-accent"
                    : "border-border text-muted hover:text-text"
                }`}
              >
                {METRIC_LABELS[key]}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-surface text-xs text-muted">
              <th className="px-3 py-2.5 font-normal"></th>
              <th className="px-3 py-2.5 font-normal">Config</th>
              <th
                className="cursor-pointer select-none px-3 py-2.5 font-normal hover:text-text"
                onClick={() => handleSort("composite_score", true)}
              >
                <span className="flex items-center gap-1">
                  Score
                  {sort.key === "composite_score" &&
                    (sort.direction === "desc" ? <ArrowDown size={11} /> : <ArrowUp size={11} />)}
                </span>
              </th>
              {visibleMetrics.map((key) => (
                <th
                  key={key}
                  className="cursor-pointer select-none px-3 py-2.5 font-normal hover:text-text"
                  onClick={() => handleSort(key, true)}
                >
                  <span className="flex items-center gap-1">
                    {METRIC_LABELS[key]}
                    {sort.key === key && (sort.direction === "desc" ? <ArrowDown size={11} /> : <ArrowUp size={11} />)}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredSortedRuns.length === 0 && (
              <tr>
                <td colSpan={3 + visibleMetrics.length} className="px-4 py-10 text-center text-muted">
                  {inProgress ? "Configs are still running…" : "No configs match the current filters."}
                </td>
              </tr>
            )}
            {filteredSortedRuns.map((run) => {
              const isBest = run.id === experiment.best_run_id;
              return (
                <tr
                  key={run.id}
                  className={`border-b border-border align-top last:border-0 hover:bg-surfaceHover ${
                    isBest ? "bg-accent/5" : ""
                  }`}
                >
                  <td className="px-3 py-3">
                    {isBest && <Star size={13} className="fill-accent text-accent" />}
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-text">
                    {run.config ? (
                      <div className="flex flex-col gap-0.5">
                        <span>
                          {run.config.chunking_strategy} · {run.config.embedding_model}
                        </span>
                        <span className="text-muted">
                          {run.config.retriever_type} · {run.config.reranker_type} · {run.config.llm_model}
                        </span>
                      </div>
                    ) : (
                      "—"
                    )}
                    <div
                      className={`mt-1 text-[11px] ${
                        run.status === "completed"
                          ? "text-success"
                          : run.status === "failed"
                          ? "text-danger"
                          : "text-warning"
                      }`}
                    >
                      {run.status}
                    </div>
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-accent">
                    {run.composite_score !== null ? `${(run.composite_score * 100).toFixed(1)}%` : "—"}
                  </td>
                  {visibleMetrics.map((key) => (
                    <td key={key} className="px-3 py-3 text-muted">
                      {formatMetric(key, run.summary_metrics?.[key])}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-muted">
        Score is a composite of nDCG@K, Correctness, Faithfulness, and (inverted) Hallucination —
        the <Star size={11} className="inline fill-accent text-accent" /> marks the highest-scoring
        config. Latency isn't part of the score since speed is a tradeoff to weigh yourself, not a
        quality signal. Cost tracking isn't built yet (Phase 12).
      </p>
    </div>
  );
}