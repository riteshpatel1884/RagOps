"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2, Pencil, X, Workflow, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const DEFAULT_FORM = {
  name: "",
  chunking_strategy: "recursive",
  embedding_model: "local-tfidf-384",
  retriever_type: "hybrid",
  reranker_type: "none",
  llm_model: "",
  chunk_size: 512,
  chunk_overlap: 64,
  top_k: 5,
};

function Select({ label, value, onChange, options }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs text-muted">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumberField({ label, value, onChange, min, max }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs text-muted">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
      />
    </label>
  );
}

export default function PipelinesPage() {
  const [options, setOptions] = useState(null);
  const [pipelines, setPipelines] = useState([]);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [opts, list] = await Promise.all([api.getPipelineOptions(), api.listPipelines()]);
      setOptions(opts);
      setPipelines(list);
      setForm((f) => (f.llm_model ? f : { ...f, llm_model: opts.llm_model[0] || "" }));
      setError(null);
    } catch (e) {
      setError("Couldn't reach the backend. Is it running on :8000?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function startEdit(p) {
    setEditingId(p.id);
    setForm({
      name: p.name,
      chunking_strategy: p.chunking_strategy,
      embedding_model: p.embedding_model,
      retriever_type: p.retriever_type,
      reranker_type: p.reranker_type,
      llm_model: p.llm_model,
      chunk_size: p.chunk_size,
      chunk_overlap: p.chunk_overlap,
      top_k: p.top_k,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm((f) => ({ ...DEFAULT_FORM, llm_model: options?.llm_model[0] || "" }));
  }

  async function handleSave() {
    if (!form.name.trim()) {
      setError("Give the pipeline a name first.");
      return;
    }
    setSaving(true);
    try {
      if (editingId) {
        await api.updatePipeline(editingId, form);
      } else {
        await api.createPipeline(form);
      }
      cancelEdit();
      await refresh();
      setError(null);
    } catch (e) {
      setError("Couldn't save that pipeline — check the backend logs.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    await api.deletePipeline(id);
    if (editingId === id) cancelEdit();
    refresh();
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <div className="mb-8">
        <h1 className="text-lg font-medium text-text">Pipelines</h1>
        <p className="mt-1 text-sm text-muted">
          Build and save RAG configurations. The Datasets upload dialog and the Playground
          both let you pick which saved pipeline to run.
        </p>
      </div>

      {error && (
        <div className="mb-4 flex items-center justify-between rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-danger hover:text-text">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="mb-10 rounded-md border border-border bg-surface p-5">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-sm text-text">{editingId ? "Edit Pipeline" : "Create Pipeline"}</span>
          {editingId && (
            <button onClick={cancelEdit} className="flex items-center gap-1 text-xs text-muted hover:text-text">
              <X size={12} /> Cancel
            </button>
          )}
        </div>

        <div className="mb-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs text-muted">Name</span>
            <input
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="e.g. Finance Hybrid v1"
              className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none"
            />
          </label>
        </div>

        {options && (
          <>
            <div className="mb-4 grid grid-cols-3 gap-4">
              <Select
                label="Chunking"
                value={form.chunking_strategy}
                onChange={(v) => set("chunking_strategy", v)}
                options={options.chunking_strategy}
              />
              <Select
                label="Embedding"
                value={form.embedding_model}
                onChange={(v) => set("embedding_model", v)}
                options={options.embedding_model}
              />
              <Select
                label="Retriever"
                value={form.retriever_type}
                onChange={(v) => set("retriever_type", v)}
                options={options.retriever_type}
              />
              <Select
                label="Reranker"
                value={form.reranker_type}
                onChange={(v) => set("reranker_type", v)}
                options={options.reranker_type}
              />
              <Select
                label="LLM"
                value={form.llm_model}
                onChange={(v) => set("llm_model", v)}
                options={options.llm_model}
              />
              <NumberField label="Top K" value={form.top_k} onChange={(v) => set("top_k", v)} min={1} max={50} />
            </div>

            <div className="mb-5 grid grid-cols-3 gap-4">
              <NumberField
                label="Chunk Size"
                value={form.chunk_size}
                onChange={(v) => set("chunk_size", v)}
                min={64}
                max={4096}
              />
              <NumberField
                label="Chunk Overlap"
                value={form.chunk_overlap}
                onChange={(v) => set("chunk_overlap", v)}
                min={0}
                max={1024}
              />
            </div>
          </>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 rounded-sm border border-accent bg-accent/10 px-3 py-2 text-sm text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          {editingId ? "Save Changes" : "Save Pipeline"}
        </button>
      </div>

      <div>
        <div className="mb-3 text-xs text-muted">Saved ({pipelines.length})</div>
        {loading && <p className="text-sm text-muted">Loading…</p>}
        {!loading && pipelines.length === 0 && (
          <p className="text-sm text-muted">No pipelines yet — create one above.</p>
        )}
        <div className="flex flex-col gap-2">
          {pipelines.map((p) => (
            <div
              key={p.id}
              className={`flex items-center justify-between rounded-md border p-4 ${
                editingId === p.id ? "border-accent bg-accent/5" : "border-border bg-surface"
              }`}
            >
              <div>
                <div className="flex items-center gap-2 text-sm text-text">
                  <Workflow size={14} className="text-accent" />
                  {p.name}
                </div>
                <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs text-muted">
                  <span>{p.chunking_strategy}</span>
                  <span>·</span>
                  <span>{p.embedding_model}</span>
                  <span>·</span>
                  <span>{p.retriever_type}</span>
                  <span>·</span>
                  <span>{p.reranker_type}</span>
                  <span>·</span>
                  <span>{p.llm_model}</span>
                  <span>·</span>
                  <span>
                    chunk={p.chunk_size}/{p.chunk_overlap}
                  </span>
                  <span>·</span>
                  <span>top_k={p.top_k}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => startEdit(p)}
                  className="text-muted transition-colors hover:text-accent"
                  title="Edit"
                >
                  <Pencil size={14} />
                </button>
                <button
                  onClick={() => handleDelete(p.id)}
                  className="text-muted transition-colors hover:text-danger"
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}