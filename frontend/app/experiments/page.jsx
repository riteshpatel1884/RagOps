"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Play, Loader2, ChevronRight, Trash2, FlaskConical } from "lucide-react";
import { api } from "@/lib/api";

const DIMENSION_LABELS = {
  chunking_strategy: "Chunking",
  embedding_model: "Embedding",
  retriever_type: "Retriever",
  reranker_type: "Reranker",
  llm_model: "LLM",
};

const DIMENSIONS = ["chunking_strategy", "embedding_model", "retriever_type", "reranker_type", "llm_model"];

function CheckboxGroup({ label, options, selected, onToggle }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs text-muted">{label}</span>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o}
            onClick={() => onToggle(o)}
            className={`rounded-sm border px-2 py-1 text-xs transition-colors ${
              selected.includes(o)
                ? "border-accent bg-accent/10 text-accent"
                : "border-border text-muted hover:text-text"
            }`}
          >
            {o}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ExperimentsPage() {
  const [options, setOptions] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [experiments, setExperiments] = useState([]);

  const [name, setName] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [sweep, setSweep] = useState({});
  const [chunkSize, setChunkSize] = useState(512);
  const [chunkOverlap, setChunkOverlap] = useState(64);
  const [topK, setTopK] = useState(5);

  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshLists = useCallback(async () => {
    try {
      const [opts, ds, exps] = await Promise.all([
        api.getExperimentOptions(),
        api.listEvalDatasets(),
        api.listExperiments(),
      ]);
      setOptions(opts);
      setDatasets(ds);
      setExperiments(exps);
      setDatasetId((cur) => cur || ds[0]?.id || "");
      setSweep((cur) =>
        Object.keys(cur).length
          ? cur
          : {
              chunking_strategy: [opts.chunking_strategy[0]],
              embedding_model: [opts.embedding_model[0]],
              retriever_type: [opts.retriever_type[0]],
              reranker_type: [opts.reranker_type[0]],
              llm_model: [opts.llm_model[0]],
            }
      );
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

  function toggleOption(dim, value) {
    setSweep((s) => {
      const current = s[dim] || [];
      const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
      return { ...s, [dim]: next };
    });
  }

  const configCount = useMemo(() => {
    if (!options) return 0;
    return DIMENSIONS.reduce((total, dim) => total * (sweep[dim]?.length || 0), 1);
  }, [sweep, options]);

  const overCap = options && configCount > options.max_configs;

  async function handleCreate() {
    if (!name.trim() || !datasetId || configCount === 0 || overCap) return;
    setCreating(true);
    setError(null);
    try {
      await api.createExperiment({
        name: name.trim(),
        dataset_id: datasetId,
        sweep,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
        top_k: topK,
      });
      setName("");
      refreshLists();
    } catch (e) {
      setError("Couldn't start that experiment — check the dataset has questions and try fewer options.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id, ev) {
    ev.preventDefault();
    ev.stopPropagation();
    await api.deleteExperiment(id);
    refreshLists();
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <div className="mb-8">
        <h1 className="text-lg font-medium text-text">Experiments</h1>
        <p className="mt-1 text-sm text-muted">
          Pick a sweep of options per dimension — every combination gets generated as a real
          pipeline and scored against your dataset automatically. Open an experiment to compare,
          sort, and export the results.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="mb-10 rounded-md border border-border bg-surface p-5">
        <div className="mb-4 text-sm text-text">Create Experiment</div>

        <div className="mb-4 grid grid-cols-2 gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-muted">Name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Chunking x Retriever Sweep"
              className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-muted">Dataset</span>
            <select
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
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
        </div>

        {options && (
          <>
            <div className="mb-5 grid grid-cols-2 gap-4">
              {DIMENSIONS.map((dim) => (
                <CheckboxGroup
                  key={dim}
                  label={DIMENSION_LABELS[dim]}
                  options={options[dim]}
                  selected={sweep[dim] || []}
                  onToggle={(v) => toggleOption(dim, v)}
                />
              ))}
            </div>

            <div className="mb-5 grid grid-cols-3 gap-4">
              <label className="flex flex-col gap-1.5">
                <span className="text-xs text-muted">Chunk Size</span>
                <input
                  type="number"
                  value={chunkSize}
                  onChange={(e) => setChunkSize(Number(e.target.value))}
                  className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs text-muted">Chunk Overlap</span>
                <input
                  type="number"
                  value={chunkOverlap}
                  onChange={(e) => setChunkOverlap(Number(e.target.value))}
                  className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-xs text-muted">Top K</span>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
                />
              </label>
            </div>

            <div className="mb-4 flex items-center justify-between">
              <span className={`text-xs ${overCap ? "text-danger" : "text-muted"}`}>
                {configCount} configuration{configCount === 1 ? "" : "s"} will be generated
                {overCap && ` — exceeds the cap of ${options.max_configs}, select fewer options`}
              </span>
              <button
                onClick={handleCreate}
                disabled={creating || !name.trim() || !datasetId || configCount === 0 || overCap}
                className="flex items-center gap-2 rounded-sm border border-accent bg-accent/10 px-4 py-2 text-sm text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
              >
                {creating ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                Run Experiment
              </button>
            </div>
          </>
        )}
      </div>

      <div>
        <div className="mb-3 text-xs text-muted">Experiments ({experiments.length})</div>
        {loading && <p className="text-sm text-muted">Loading…</p>}
        {!loading && experiments.length === 0 && <p className="text-sm text-muted">No experiments yet.</p>}
        <div className="flex flex-col gap-2">
          {experiments.map((exp) => (
            <Link
              key={exp.id}
              href={`/experiments/${exp.id}`}
              className="flex items-center justify-between rounded-md border border-border bg-surface p-4 transition-colors hover:bg-surfaceHover"
            >
              <div>
                <div className="flex items-center gap-2 text-sm text-text">
                  <FlaskConical size={14} className="text-accent" />
                  {exp.name}
                </div>
                <div className="mt-1 flex items-center gap-2 text-xs text-muted">
                  <span>{exp.dataset_name}</span>
                  <span>·</span>
                  <span
                    className={
                      exp.status === "completed"
                        ? "text-success"
                        : exp.status === "failed"
                        ? "text-danger"
                        : "text-warning"
                    }
                  >
                    {exp.status} · {exp.completed_configs}/{exp.total_configs}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button onClick={(e) => handleDelete(exp.id, e)} className="text-muted hover:text-danger">
                  <Trash2 size={14} />
                </button>
                <ChevronRight size={14} className="text-muted" />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}