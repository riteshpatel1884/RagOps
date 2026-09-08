"use client";

import { useEffect, useState } from "react";
import { Send, Loader2, FileText } from "lucide-react";
import { api } from "@/lib/api";

export default function PlaygroundPage() {
  const [question, setQuestion] = useState("");
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipeline, setSelectedPipeline] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .listPipelines()
      .then((list) => {
        setPipelines(list);
        setSelectedPipeline(list[0]?.id || "");
      })
      .catch(() => setError("Couldn't reach the backend. Is it running on :8000?"));
  }, []);

  async function handleAsk() {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.ask(question.trim(), selectedPipeline);
      setResult(res);
    } catch (e) {
      setError("Couldn't reach the backend. Is it running on :8000?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <div className="mb-6">
        <h1 className="text-lg font-medium text-text">RAG Playground</h1>
        <p className="mt-1 text-sm text-muted">
          Ask a question against everything indexed in Datasets, using the pipeline below.
        </p>
      </div>

      <div className="mb-4">
        <label className="flex flex-col gap-1.5">
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
              <span className="font-mono text-accent">{result.pipeline}</span>
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
