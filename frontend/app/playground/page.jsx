"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Send, Loader2, FileText, Trash2, Pencil } from "lucide-react";
import { api } from "@/lib/api";

export default function PlaygroundPage() {
  const [question, setQuestion] = useState("");
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipeline, setSelectedPipeline] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refreshPipelines = useCallback(
    async (keepSelection = true) => {
      try {
        const list = await api.listPipelines();
        setPipelines(list);
        setSelectedPipeline((cur) => {
          if (keepSelection && list.some((p) => p.id === cur)) return cur;
          return list[0]?.id || "";
        });
      } catch (e) {
        setError("Couldn't reach the backend. Is it running on :8000?");
      }
    },
    []
  );

  useEffect(() => {
    refreshPipelines(false);
  }, [refreshPipelines]);

  async function handleAsk() {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.ask(question.trim(), selectedPipeline);
      setResult(res);
    } catch (e) {
      setError(
        "That pipeline's request failed — often this means its LLM model is no longer valid on Groq. Try editing or deleting it below."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteSelected() {
    if (!selectedPipeline) return;
    await api.deletePipeline(selectedPipeline);
    setResult(null);
    setError(null);
    refreshPipelines(false);
  }

  const activePipeline = pipelines.find((p) => p.id === selectedPipeline);

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <div className="mb-6">
        <h1 className="text-lg font-medium text-text">RAG Playground</h1>
        <p className="mt-1 text-sm text-muted">
          Ask a question against everything indexed in Datasets, using the pipeline below.
        </p>
      </div>

      <div className="mb-4 flex items-end gap-2">
        <label className="flex flex-1 flex-col gap-1.5">
          <span className="text-xs text-muted">Pipeline</span>
          <select
            value={selectedPipeline}
            onChange={(e) => setSelectedPipeline(e.target.value)}
            className="rounded-sm border border-border bg-surface px-3 py-2.5 text-sm text-text focus:border-accent focus:outline-none"
          >
            {pipelines.length === 0 && <option value="">No pipelines yet</option>}
            {pipelines.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} · {p.retriever_type}/{p.reranker_type}/{p.llm_model}
              </option>
            ))}
          </select>
        </label>
        <Link
          href="/pipelines"
          title="Edit this pipeline"
          className="flex items-center justify-center rounded-sm border border-border bg-surface p-2.5 text-muted transition-colors hover:text-accent"
        >
          <Pencil size={15} />
        </Link>
        <button
          onClick={handleDeleteSelected}
          disabled={!selectedPipeline}
          title="Delete this pipeline"
          className="flex items-center justify-center rounded-sm border border-border bg-surface p-2.5 text-muted transition-colors hover:text-danger disabled:opacity-50"
        >
          <Trash2 size={15} />
        </button>
      </div>

      <div className="mb-6 flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="Ask a question…"
          className="flex-1 rounded-sm border border-border bg-surface px-3 py-2.5 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none"
        />
        <button
          onClick={handleAsk}
          disabled={loading || !question.trim() || !selectedPipeline}
          className="flex items-center gap-2 rounded-sm border border-accent bg-accent/10 px-4 py-2.5 text-sm text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          Run
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {result && (
        <div className="flex flex-col gap-4">
          <div className="rounded-md border border-border bg-surface p-4">
            <div className="mb-2 flex items-center justify-between text-xs text-muted">
              <span>Answer</span>
              <span className="flex items-center gap-2">
                <span className="font-mono text-accent">{result.pipeline}</span>
                {result.trace_id && (
                  <span className="font-mono text-[10px] text-muted" title="Trace ID — full trace browser lands in Phase 8">
                    trace: {result.trace_id.slice(0, 8)}
                  </span>
                )}
              </span>
            </div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-text">
              {result.answer}
            </p>
          </div>

          <div>
            <div className="mb-2 text-xs text-muted">
              Sources ({result.sources.length})
            </div>
            <div className="flex flex-col gap-2">
              {result.sources.map((s, i) => (
                <div
                  key={i}
                  className="rounded-md border border-border bg-surface p-3 text-sm"
                >
                  <div className="mb-1.5 flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-text">
                      <FileText size={13} className="text-muted" />
                      {s.filename}
                      <span className="text-muted">· p.{s.page_number}</span>
                    </span>
                    <span className="font-mono text-xs text-accent">
                      {s.score.toFixed(3)}
                    </span>
                  </div>
                  <p className="line-clamp-3 text-xs text-muted">{s.text}</p>
                </div>
              ))}
              {result.sources.length === 0 && (
                <p className="text-sm text-muted">
                  No matching chunks — upload documents in Datasets first.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}