"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Upload, FileText, Trash2, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const STATUS_STYLE = {
  ready: "text-success border-success/30 bg-success/10",
  processing: "text-warning border-warning/30 bg-warning/10",
  failed: "text-danger border-danger/30 bg-danger/10",
};

export default function DatasetsPage() {
  const [docs, setDocs] = useState([]);
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipeline, setSelectedPipeline] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const fileInput = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const [docList, pipelineList] = await Promise.all([
        api.listDocuments(),
        api.listPipelines(),
      ]);
      setDocs(docList);
      setPipelines(pipelineList);
      setSelectedPipeline((current) => current || pipelineList[0]?.id || "");
      setError(null);
    } catch (e) {
      setError("Couldn't reach the backend. Is it running on :8000?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    // documents finish processing async server-side; poll while any are in-flight
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
  }, [refresh]);

  async function handleUpload(file) {
    setUploading(true);
    try {
      await api.uploadDocument(file, selectedPipeline);
      await refresh();
    } catch (e) {
      setError("Upload failed. Only PDF files are supported in Phase 1.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    await api.deleteDocument(id);
    refresh();
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-lg font-medium text-text">Datasets</h1>
          <p className="mt-1 text-sm text-muted">
            Upload source documents. Each one is parsed, chunked, embedded, and indexed
            automatically using the pipeline you pick below.
          </p>
        </div>
      </div>

      <div className="mb-6 flex items-end gap-3">
        <label className="flex flex-1 flex-col gap-1.5">
          <span className="text-xs text-muted">Ingest with pipeline</span>
          <select
            value={selectedPipeline}
            onChange={(e) => setSelectedPipeline(e.target.value)}
            className="rounded-sm border border-border bg-surface px-3 py-2.5 text-sm text-text focus:border-accent focus:outline-none"
          >
            {pipelines.length === 0 && <option value="">No pipelines yet</option>}
            {pipelines.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} · {p.chunking_strategy}/{p.embedding_model}
              </option>
            ))}
          </select>
        </label>

        <button
          onClick={() => fileInput.current?.click()}
          disabled={uploading || pipelines.length === 0}
          className="flex items-center gap-2 rounded-sm border border-accent bg-accent/10 px-3 py-2.5 text-sm text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
        >
          {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          Upload document
        </button>
        <input
          ref={fileInput}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleUpload(file);
            e.target.value = "";
          }}
        />
      </div>

      {pipelines.length === 0 && !loading && (
        <div className="mb-4 rounded-sm border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
          No pipelines saved yet — create one under Pipelines before uploading.
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-md border border-border">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-surface text-xs text-muted">
              <th className="px-4 py-2.5 font-normal">Document</th>
              <th className="px-4 py-2.5 font-normal">Pages</th>
              <th className="px-4 py-2.5 font-normal">Status</th>
              <th className="px-4 py-2.5 font-normal"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-muted">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && docs.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-muted">
                  No documents yet. Upload a PDF to build your first index.
                </td>
              </tr>
            )}
            {docs.map((d) => (
              <tr key={d.id} className="border-b border-border last:border-0 hover:bg-surfaceHover">
                <td className="flex items-center gap-2 px-4 py-3 text-text">
                  <FileText size={14} className="text-muted" />
                  {d.filename}
                </td>
                <td className="px-4 py-3 text-muted">{d.page_count || "—"}</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-sm border px-2 py-0.5 text-xs ${STATUS_STYLE[d.status]}`}
                  >
                    {d.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => handleDelete(d.id)}
                    className="text-muted transition-colors hover:text-danger"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
