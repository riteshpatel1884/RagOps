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
};
