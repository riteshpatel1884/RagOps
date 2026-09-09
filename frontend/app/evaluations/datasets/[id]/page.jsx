"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Upload, Plus, Pencil, Trash2, X, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const EMPTY_FORM = {
  question: "",
  ground_truth_answer: "",
  relevant_document_ids: [],
  relevant_chunk_ids_text: "",
};

export default function EvalDatasetDetailPage({ params }) {
  const { id } = params;

  const [dataset, setDataset] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const fileInput = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const [ds, docs] = await Promise.all([api.getEvalDataset(id), api.listDocuments()]);
      setDataset(ds);
      setDocuments(docs);
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

  function toggleDoc(docId) {
    setForm((f) => ({
      ...f,
      relevant_document_ids: f.relevant_document_ids.includes(docId)
        ? f.relevant_document_ids.filter((d) => d !== docId)
        : [...f.relevant_document_ids, docId],
    }));
  }

  function startEdit(q) {
    setEditingId(q.id);
    setForm({
      question: q.question,
      ground_truth_answer: q.ground_truth_answer,
      relevant_document_ids: q.relevant_document_ids,
      relevant_chunk_ids_text: (q.relevant_chunk_ids || []).join(", "),
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function handleSave() {
    if (!form.question.trim()) return;
    setSaving(true);
    const payload = {
      question: form.question.trim(),
      ground_truth_answer: form.ground_truth_answer.trim(),
      relevant_document_ids: form.relevant_document_ids,
      relevant_chunk_ids: form.relevant_chunk_ids_text
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    try {
      if (editingId) {
        await api.updateEvalQuestion(id, editingId, payload);
      } else {
        await api.addEvalQuestion(id, payload);
      }
      cancelEdit();
      await refresh();
    } catch (e) {
      setError("Couldn't save that question.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(questionId) {
    await api.deleteEvalQuestion(id, questionId);
    refresh();
  }

  async function handleUpload(file) {
    setUploading(true);
    try {
      const result = await api.uploadEvalQuestions(id, file);
      await refresh();
      if (result.unresolved_document_refs > 0) {
        setError(
          `Imported ${result.created} questions, but ${result.unresolved_document_refs} relevant_documents reference(s) didn't match an uploaded document by id or filename.`
        );
      } else {
        setError(null);
      }
    } catch (e) {
      setError("Upload failed — check the file is a valid .csv or .json.");
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return <div className="mx-auto max-w-4xl px-8 py-10 text-sm text-muted">Loading…</div>;
  }

  if (!dataset) {
    return (
      <div className="mx-auto max-w-4xl px-8 py-10 text-sm text-danger">
        {error || "Dataset not found."}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <Link href="/evaluations/datasets" className="mb-4 flex items-center gap-1.5 text-xs text-muted hover:text-text">
        <ArrowLeft size={12} /> All datasets
      </Link>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-lg font-medium text-text">{dataset.name}</h1>
          <p className="mt-1 text-sm text-muted">{dataset.question_count} questions</p>
        </div>
        <button
          onClick={() => fileInput.current?.click()}
          disabled={uploading}
          className="flex items-center gap-2 rounded-sm border border-accent bg-accent/10 px-3 py-2 text-sm text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
        >
          {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          Upload CSV / JSON
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".csv,.json"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleUpload(file);
            e.target.value = "";
          }}
        />
      </div>

      {error && (
        <div className="mb-4 rounded-sm border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="mb-8 rounded-md border border-border bg-surface p-5">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-sm text-text">{editingId ? "Edit Question" : "Add Question"}</span>
          {editingId && (
            <button onClick={cancelEdit} className="text-muted hover:text-text">
              <X size={14} />
            </button>
          )}
        </div>

        <div className="mb-3 flex flex-col gap-1.5">
          <span className="text-xs text-muted">Question</span>
          <textarea
            value={form.question}
            onChange={(e) => setForm((f) => ({ ...f, question: e.target.value }))}
            rows={2}
            className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
          />
        </div>

        <div className="mb-3 flex flex-col gap-1.5">
          <span className="text-xs text-muted">Ground Truth Answer</span>
          <textarea
            value={form.ground_truth_answer}
            onChange={(e) => setForm((f) => ({ ...f, ground_truth_answer: e.target.value }))}
            rows={2}
            className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text focus:border-accent focus:outline-none"
          />
        </div>

        <div className="mb-3 flex flex-col gap-1.5">
          <span className="text-xs text-muted">Relevant Documents</span>
          {documents.length === 0 ? (
            <p className="text-xs text-muted">No documents uploaded yet — see Datasets.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {documents.map((d) => (
                <button
                  key={d.id}
                  onClick={() => toggleDoc(d.id)}
                  className={`rounded-sm border px-2 py-1 text-xs transition-colors ${
                    form.relevant_document_ids.includes(d.id)
                      ? "border-accent bg-accent/10 text-accent"
                      : "border-border text-muted hover:text-text"
                  }`}
                >
                  {d.filename}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="mb-4 flex flex-col gap-1.5">
          <span className="text-xs text-muted">Relevant Chunks (optional, comma-separated chunk IDs)</span>
          <input
            value={form.relevant_chunk_ids_text}
            onChange={(e) => setForm((f) => ({ ...f, relevant_chunk_ids_text: e.target.value }))}
            placeholder="chunk_183, chunk_412"
            className="rounded-sm border border-border bg-bg px-3 py-2 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none"
          />
        </div>

        <button
          onClick={handleSave}
          disabled={saving || !form.question.trim()}
          className="flex items-center gap-2 rounded-sm border border-accent bg-accent/10 px-3 py-2 text-sm text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
          {editingId ? "Save Changes" : "Add Question"}
        </button>
      </div>

      <div className="overflow-hidden rounded-md border border-border">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border bg-surface text-xs text-muted">
              <th className="px-4 py-2.5 font-normal">Question</th>
              <th className="px-4 py-2.5 font-normal">Ground Truth</th>
              <th className="px-4 py-2.5 font-normal">Relevant Docs</th>
              <th className="px-4 py-2.5 font-normal"></th>
            </tr>
          </thead>
          <tbody>
            {dataset.questions.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-muted">
                  No questions yet — add one above or upload a CSV/JSON file.
                </td>
              </tr>
            )}
            {dataset.questions.map((q) => (
              <tr key={q.id} className="border-b border-border last:border-0 align-top hover:bg-surfaceHover">
                <td className="max-w-xs px-4 py-3 text-text">{q.question}</td>
                <td className="max-w-xs px-4 py-3 text-muted">{q.ground_truth_answer || "—"}</td>
                <td className="px-4 py-3 text-muted">
                  {q.relevant_documents.length > 0 ? q.relevant_documents.join(", ") : "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button onClick={() => startEdit(q)} className="text-muted hover:text-accent">
                      <Pencil size={14} />
                    </button>
                    <button onClick={() => handleDelete(q.id)} className="text-muted hover:text-danger">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
