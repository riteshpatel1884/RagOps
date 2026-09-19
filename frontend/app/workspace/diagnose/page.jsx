"use client";

import { useEffect, useState } from "react";
import Card from "@/components/Card";
import { Button, ErrorBanner, Spinner } from "@/components/ui";
import { LabeledSelect } from "@/components/FormControls";
import { api } from "@/lib/api";

const METRIC_OPTIONS = ["recall", "precision", "mrr", "ndcg", "faithfulness", "relevance"];

export default function DiagnosePage() {
  const [experiments, setExperiments] = useState([]);
  const [filename, setFilename] = useState("");
  const [metricX, setMetricX] = useState("recall");
  const [metricY, setMetricY] = useState("faithfulness");
  const [judge, setJudge] = useState("offline");

  const [report, setReport] = useState(null);
  const [followUp, setFollowUp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .listExperiments()
      .then((list) => {
        setExperiments(list);
        if (list.length > 0) setFilename(list[0].filename);
      })
      .catch(() => {});
  }, []);

  async function runDiagnosis() {
    if (!filename) return;
    setLoading(true);
    setError(null);
    setReport(null);
    setFollowUp(null);
    try {
      const res = await api.diagnose({ filename, metric_x: metricX, metric_y: metricY });
      setReport(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function runAutoFollowUp() {
    if (!filename) return;
    setFollowUpLoading(true);
    setError(null);
    setFollowUp(null);
    try {
      const res = await api.autoFollowUp({ filename, metric_x: metricX, metric_y: metricY, judge });
      setFollowUp(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setFollowUpLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Diagnose</h1>
        <p className="mt-1 text-sm text-slate-500">
          Pick a saved experiment sweep to see per-config bottleneck diagnoses and the Pareto frontier between two
          metrics.
        </p>
      </div>

      {error && <ErrorBanner message={error} />}

      {experiments.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-400">
            No saved experiments yet — run a sweep on the Experiment page first.
          </p>
        </Card>
      ) : (
        <Card title="Choose a sweep">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <LabeledSelect
              label="Experiment file"
              value={filename}
              onChange={setFilename}
              options={experiments.map((e) => ({ value: e.filename, label: e.filename }))}
            />
            <LabeledSelect label="Metric X" value={metricX} onChange={setMetricX} options={METRIC_OPTIONS.map((m) => ({ value: m, label: m }))} />
            <LabeledSelect label="Metric Y" value={metricY} onChange={setMetricY} options={METRIC_OPTIONS.map((m) => ({ value: m, label: m }))} />
            <LabeledSelect
              label="Follow-up judge"
              value={judge}
              onChange={setJudge}
              options={[
                { value: "offline", label: "Offline" },
                { value: "llm", label: "LLM (must match original sweep)" },
              ]}
            />
          </div>
          <div className="mt-4 flex gap-3">
            <Button onClick={runDiagnosis} disabled={loading}>
              Diagnose
            </Button>
            <Button variant="secondary" onClick={runAutoFollowUp} disabled={followUpLoading}>
              Auto follow-up (run best suggestion live)
            </Button>
          </div>
          {(loading || followUpLoading) && (
            <div className="mt-4">
              <Spinner />
            </div>
          )}
        </Card>
      )}

      {followUp && (
        <Card title="Auto follow-up result">
          <p className="text-sm text-slate-600">
            Worst config by <strong>{metricX}</strong>: chunk={followUp.worst_config.chunk_size}/
            {followUp.worst_config.chunk_overlap}, top_k={followUp.worst_config.top_k}, embedder=
            {followUp.worst_config.embedder_name}, generator={followUp.worst_config.generator_name}
          </p>
          <DiagnosisBlock diagnosis={followUp.diagnosis} />

          {followUp.followed_up && followUp.before_after ? (
            <div className="mt-4">
              <p className="mb-2 text-sm font-medium text-slate-700">
                Ran: {followUp.suggestion?.label} → new config: chunk={followUp.new_config?.chunk_size}/
                {followUp.new_config?.chunk_overlap}, top_k={followUp.new_config?.top_k}, embedder=
                {followUp.new_config?.embedder_name}
              </p>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase text-slate-500">
                    <th className="py-2 pr-4">Metric</th>
                    <th className="py-2 pr-4">Before</th>
                    <th className="py-2 pr-4">After</th>
                    <th className="py-2 pr-4">Change</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(followUp.before_after).map(([metric, v]) => (
                    <tr key={metric} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-medium text-slate-700">{metric}</td>
                      <td className="py-2 pr-4">{v.before.toFixed(3)}</td>
                      <td className="py-2 pr-4">{v.after.toFixed(3)}</td>
                      <td className={`py-2 pr-4 font-medium ${v.change >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {v.change >= 0 ? "+" : ""}
                        {v.change.toFixed(3)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-400">{followUp.message}</p>
          )}
        </Card>
      )}

      {report && (
        <>
          <Card title="Pareto frontier">
            {report.frontier === null ? (
              <p className="text-sm text-slate-400">{report.tradeoff}</p>
            ) : (
              <>
                <p className="mb-3 text-xs text-slate-500">
                  Configs where no other config is at least as good on both {metricX} and {metricY} — everything
                  else is dominated.
                </p>
                <ul className="space-y-2">
                  {report.frontier.map((r, i) => (
                    <li key={i} className="rounded-md bg-slate-50 px-3 py-2 text-sm">
                      chunk={r.config.chunk_size}/{r.config.chunk_overlap}, top_k={r.config.top_k}, embedder=
                      {r.config.embedder_name}, generator={r.config.generator_name} —{" "}
                      <strong>
                        {metricX}={r[metricX]?.toFixed(3)}, {metricY}={r[metricY]?.toFixed(3)}
                      </strong>
                    </li>
                  ))}
                </ul>
                {report.tradeoff && <p className="mt-3 text-sm text-slate-600">{report.tradeoff}</p>}
              </>
            )}
          </Card>

          <Card title={`Per-config diagnosis (${report.per_config.length})`}>
            <div className="space-y-4">
              {report.per_config.map((entry, i) => (
                <div key={i} className="rounded-lg border border-slate-200 p-4">
                  <p className="text-sm font-medium text-slate-800">
                    chunk={entry.config.chunk_size}/{entry.config.chunk_overlap}, top_k={entry.config.top_k},
                    embedder={entry.config.embedder_name}, generator={entry.config.generator_name}
                  </p>
                  <DiagnosisBlock diagnosis={entry.diagnosis} />
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function DiagnosisBlock({ diagnosis }) {
  const isClean = diagnosis.bottleneck === "None detected";
  return (
    <div className="mt-2">
      <span
        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
          isClean ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
        }`}
      >
        {diagnosis.bottleneck}
      </span>
      {diagnosis.evidence.length > 0 && (
        <ul className="mt-2 list-inside list-disc text-xs text-slate-600">
          {diagnosis.evidence.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}
      {diagnosis.suggested_experiments.length > 0 && (
        <ul className="mt-2 list-inside list-decimal text-xs text-brand-700">
          {diagnosis.suggested_experiments.map((s, i) => (
            <li key={i}>{s.label}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
