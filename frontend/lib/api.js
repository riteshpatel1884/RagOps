async function json(res) {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  listDocuments: () => fetch("/api/datasets").then((r) => json(r)),

  uploadDocument: (file, pipelineId) => {
    const form = new FormData();
    form.append("file", file);
    if (pipelineId) form.append("pipeline_id", pipelineId);
    return fetch("/api/datasets/upload", { method: "POST", body: form }).then((r) => json(r));
  },

  deleteDocument: (id) =>
    fetch(`/api/datasets/${id}`, { method: "DELETE" }).then((r) => json(r)),

  ask: (question, pipelineId) =>
    fetch("/api/playground/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, pipeline_id: pipelineId }),
    }).then((r) => json(r)),

  listPipelines: () => fetch("/api/pipelines").then((r) => json(r)),

  createPipeline: (pipeline) =>
    fetch("/api/pipelines", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pipeline),
    }).then((r) => json(r)),

  deletePipeline: (id) =>
    fetch(`/api/pipelines/${id}`, { method: "DELETE" }).then((r) => json(r)),

  getPipelineOptions: () => fetch("/api/pipelines/options").then((r) => json(r)),

  listEvalDatasets: () => fetch("/api/evaluations/datasets").then((r) => json(r)),

  createEvalDataset: (name) =>
    fetch("/api/evaluations/datasets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }).then((r) => json(r)),

  deleteEvalDataset: (id) =>
    fetch(`/api/evaluations/datasets/${id}`, { method: "DELETE" }).then((r) => json(r)),

  getEvalDataset: (id) => fetch(`/api/evaluations/datasets/${id}`).then((r) => json(r)),

  addEvalQuestion: (datasetId, question) =>
    fetch(`/api/evaluations/datasets/${datasetId}/questions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(question),
    }).then((r) => json(r)),

  updateEvalQuestion: (datasetId, questionId, question) =>
    fetch(`/api/evaluations/datasets/${datasetId}/questions/${questionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(question),
    }).then((r) => json(r)),

  deleteEvalQuestion: (datasetId, questionId) =>
    fetch(`/api/evaluations/datasets/${datasetId}/questions/${questionId}`, {
      method: "DELETE",
    }).then((r) => json(r)),

  uploadEvalQuestions: (datasetId, file) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`/api/evaluations/datasets/${datasetId}/upload`, {
      method: "POST",
      body: form,
    }).then((r) => json(r));
  },

  listEvalRuns: () => fetch("/api/evaluations/runs").then((r) => json(r)),

  createEvalRun: (pipelineId, datasetId) =>
    fetch("/api/evaluations/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pipeline_id: pipelineId, dataset_id: datasetId }),
    }).then((r) => json(r)),

  getEvalRun: (id) => fetch(`/api/evaluations/runs/${id}`).then((r) => json(r)),

  deleteEvalRun: (id) => fetch(`/api/evaluations/runs/${id}`, { method: "DELETE" }).then((r) => json(r)),
};