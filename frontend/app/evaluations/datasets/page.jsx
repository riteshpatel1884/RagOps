"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus, Trash2, FileQuestion, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

export default function EvalDatasetsPage() {
  const [datasets, setDatasets] = useState([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const list = await api.listEvalDatasets();
      setDatasets(list);
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

  async function handleCreate() {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await api.createEvalDataset(name.trim());
      setName("");
      await refresh();
    } catch (e) {
      setError("Couldn't create that dataset.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id) {
    await api.deleteEvalDataset(id);
    refresh();
  }

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <div className="mb-8">
        <h1 className="text-lg font-medium text-text">Evaluation Datasets</h1>
        <p className="mt-1 text-sm text-muted">
          Ground-truth question/answer pairs, with labeled relevant documents and chunks.
          Phase 4's evaluation engine scores pipelines against whichever dataset you pick here.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="mb-8 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          placeholder="e.g. Finance-QA-v1"
          className="flex-1 rounded-sm border border-border bg-surface px-3 py-2.5 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none"
        />
        <button
          onClick={handleCreate}
          disabled={creating || !name.trim()}
          className="flex items-center gap-2 rounded-sm border border-accent bg-accent/10 px-4 py-2.5 text-sm text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
        >
          {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          Create Dataset
        </button>
      </div>

      {loading && <p className="text-sm text-muted">Loading…</p>}
      {!loading && datasets.length === 0 && (
        <p className="text-sm text-muted">No datasets yet — create one above.</p>
      )}

      <div className="flex flex-col gap-2">
        {datasets.map((ds) => (
          <div
            key={ds.id}
            className="flex items-center justify-between rounded-md border border-border bg-surface p-4"
          >
            <Link href={`/evaluations/datasets/${ds.id}`} className="flex-1">
              <div className="flex items-center gap-2 text-sm text-text">
                <FileQuestion size={14} className="text-accent" />
                {ds.name}
              </div>
              <div className="mt-1 text-xs text-muted">{ds.question_count} questions</div>
            </Link>
            <button
              onClick={() => handleDelete(ds.id)}
              className="text-muted transition-colors hover:text-danger"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
