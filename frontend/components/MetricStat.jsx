export default function MetricStat({ label, value, format = "decimal" }) {
  let display = "—";
  if (value !== undefined && value !== null) {
    if (format === "percent") display = `${(value * 100).toFixed(1)}%`;
    else if (format === "seconds") display = `${value.toFixed(2)}s`;
    else display = value.toFixed(3);
  }

  return (
    <div className="rounded-lg border border-border bg-slate-50 px-4 py-3">
      <div className="text-xs font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-text">{display}</div>
    </div>
  );
}
