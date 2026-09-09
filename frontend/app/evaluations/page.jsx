// import PhasePlaceholder from "@/components/PhasePlaceholder";

// export default function Page() {
//   return (
//     <PhasePlaceholder
//       title="Evaluation"
//       phase="Phase 3–4 — Evaluation Dataset & Engine"
//       description="Retrieval and generation metrics: Recall@K, MRR, nDCG, faithfulness, hallucination rate."
//     />
//   );
// }



"use client";

import { useCallback, useEffect, useState } from "react";
import { Play, Loader2, ChevronRight, Trash2 } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
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
};

const HEADLINE_KEYS = ["answer_correctness", "faithfulness", "recall_at_k", "mrr", "hallucination_rate"];

function pct(v) {
  return v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`;
}

function MetricCard({ label, value, danger }) {
  return (
    <div className="rounded-md border border-border bg-surface p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className={`mt-1 text-xl ${danger ? "text-danger" : "text-text"}`}>{pct(value)}</div>
    </div>
  );
}

export default function EvaluationsPage() {
  const [pipelines, setPipelines] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [selectedPipeline, setSelectedPipeline] = useState("");
  const [selectedDataset, setSelectedDataset] = useState("");
  const [runs, setRuns] = useState([]);
  const [activeRun, setActiveRun] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshLists = useCallback(async () => {
    try {
      const [p, d, r] = await Promise.all([
        api.listPipelines(),
        api.listEvalDatasets(),
        api.listEvalRuns(),
      ]);
      setPipelines(p);
      setDatasets(d);
      setRuns(r);
      setSelectedPipeline((cur) => cur || p[0]?.id || "");
      setSelectedDataset((cur) => cur || d[0]?.id || "");
      setError(null);
    } catch (e) {
      setError("Couldn't reach the backend. Is it running on :8000?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshLists();
  }, [refreshLists]);

  // poll the active run while it's still running
  useEffect(() => {
    if (!activeRun || activeRun.status !== "running") return;
    const interval = setInterval(async () => {
      const updated = await api.getEvalRun(activeRun.id);
      setActiveRun(updated);
      if (updated.status !== "running") {
        refreshLists();
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [activeRun, refreshLists]);

  async function handleRun() {
    if (!selectedPipeline || !selectedDataset) return;
    setRunning(true);
    setError(null);
    try {
      const created = await api.createEvalRun(selectedPipeline, selectedDataset);
      const detail = await api.getEvalRun(created.id);
      setActiveRun(detail);
      refreshLists();
    } catch (e) {
      setError("Couldn't start that evaluation run — check the dataset has questions.");
    } finally {
      setRunning(false);
    }
  }

  async function openRun(runId) {
    const detail = await api.getEvalRun(runId);
    setActiveRun(detail);
  }

  async function handleDeleteRun(runId, ev) {
    ev.stopPropagation();
    await api.deleteEvalRun(runId);
    if (activeRun?.id === runId) setActiveRun(null);
    refreshLists();
  }

  const chartData = activeRun
    ? Object.entries(activeRun.summary_metrics || {})
        .filter(([, v]) => v !== null && v !== undefined)
        .map(([key, v]) => ({ metric: METRIC_LABELS[key] || key, value: Math.round(v * 1000) / 10 }))
    : [];

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <div className="mb-8">
        <h1 className="text-lg font-medium text-text">Evaluation</h1>
        <p className="mt-1 text-sm text-muted">
          Run a saved pipeline against a saved evaluation dataset and get real retrieval and
          generation metrics back.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="mb-8 flex items-end gap-3 rounded-md border border-border bg-surface p-4">
        <label className="flex flex-1 flex-col gap-1.5">
          <span className="text-xs text-muted">Pipeline</span>
          <select
            value={selectedPipeline}
            onChange={(e) => setSelectedPipeline(e.target.value)}
            className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
          >
            {pipelines.length === 0 && <option value="">No pipelines yet</option>}
            {pipelines.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-1 flex-col gap-1.5">
          <span className="text-xs text-muted">Dataset</span>
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
          >
            {datasets.length === 0 && <option value="">No datasets yet</option>}
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.question_count})
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={handleRun}
          disabled={running || !selectedPipeline || !selectedDataset}
          className="flex items-center gap-2 rounded-sm border border-accent bg-accent/10 px-4 py-2 text-sm text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
        >
          {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          Run Evaluation
        </button>
      </div>

      <div className="grid grid-cols-[240px_1fr] gap-6">
        <div>
          <div className="mb-2 text-xs text-muted">Runs</div>
          {loading && <p className="text-sm text-muted">Loading…</p>}
          {!loading && runs.length === 0 && <p className="text-sm text-muted">No runs yet.</p>}
          <div className="flex flex-col gap-1.5">
            {runs.map((r) => (
              <button
                key={r.id}
                onClick={() => openRun(r.id)}
                className={`flex items-center justify-between rounded-sm border px-3 py-2 text-left text-xs transition-colors ${
                  activeRun?.id === r.id
                    ? "border-accent bg-accent/10 text-text"
                    : "border-border text-muted hover:text-text"
                }`}
              >
                <span className="truncate">
                  <span className="block truncate text-text">{r.pipeline_name}</span>
                  <span className="block truncate">{r.dataset_name}</span>
                  <span
                    className={
                      r.status === "completed"
                        ? "text-success"
                        : r.status === "failed"
                        ? "text-danger"
                        : "text-warning"
                    }
                  >
                    {r.status}
                  </span>
                </span>
                <span className="flex items-center gap-1">
                  <Trash2
                    size={12}
                    className="text-muted hover:text-danger"
                    onClick={(e) => handleDeleteRun(r.id, e)}
                  />
                  <ChevronRight size={12} />
                </span>
              </button>
            ))}
          </div>
        </div>

        <div>
          {!activeRun && (
            <div className="rounded-md border border-dashed border-border p-10 text-center text-sm text-muted">
              Run an evaluation, or pick a past run on the left, to see metrics here.
            </div>
          )}

          {activeRun && activeRun.status === "running" && (
            <div className="flex items-center gap-2 rounded-md border border-border bg-surface p-6 text-sm text-muted">
              <Loader2 size={14} className="animate-spin" />
              Scoring {activeRun.question_count} questions against {activeRun.pipeline_name}…
            </div>
          )}

          {activeRun && activeRun.status === "failed" && (
            <div className="rounded-md border border-danger/30 bg-danger/10 p-4 text-sm text-danger">
              This run failed — check the backend logs.
            </div>
          )}

          {activeRun && activeRun.status === "completed" && (
            <>
              <div className="mb-6 grid grid-cols-5 gap-3">
                {HEADLINE_KEYS.map((key) => (
                  <MetricCard
                    key={key}
                    label={METRIC_LABELS[key]}
                    value={activeRun.summary_metrics[key]}
                    danger={key === "hallucination_rate"}
                  />
                ))}
              </div>

              <div className="mb-6 rounded-md border border-border bg-surface p-4">
                <div className="mb-3 text-xs text-muted">All metrics (%)</div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#232838" />
                    <XAxis dataKey="metric" tick={{ fill: "#8189A0", fontSize: 11 }} interval={0} angle={-30} textAnchor="end" height={60} />
                    <YAxis tick={{ fill: "#8189A0", fontSize: 11 }} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{ background: "#12161F", border: "1px solid #232838", fontSize: 12 }}
                      labelStyle={{ color: "#E4E7EE" }}
                    />
                    <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                      {chartData.map((entry, i) => (
                        <Cell key={i} fill={entry.metric === "Hallucination" ? "#F87171" : "#7C8CF8"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="overflow-hidden rounded-md border border-border">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-border bg-surface text-xs text-muted">
                      <th className="px-4 py-2.5 font-normal">Question</th>
                      <th className="px-4 py-2.5 font-normal">Answer</th>
                      <th className="px-4 py-2.5 font-normal">Correctness</th>
                      <th className="px-4 py-2.5 font-normal">Faithfulness</th>
                      <th className="px-4 py-2.5 font-normal">Recall@K</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeRun.results.map((res) => (
                      <tr key={res.id} className="border-b border-border align-top last:border-0 hover:bg-surfaceHover">
                        <td className="max-w-xs px-4 py-3 text-text">{res.question}</td>
                        <td className="max-w-xs px-4 py-3 text-muted line-clamp-2">{res.answer}</td>
                        <td className="px-4 py-3 text-muted">{pct(res.generation_metrics.answer_correctness)}</td>
                        <td className="px-4 py-3 text-muted">
                          {pct(res.generation_metrics.faithfulness)}
                          {res.generation_metrics.faithfulness_source === "llm_judge" && (
                            <span className="ml-1 text-[10px] text-accent">LLM</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-muted">{pct(res.retrieval_metrics.recall_at_k)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}