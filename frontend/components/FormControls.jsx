export function LabeledInput({ label, value, onChange, type = "text" }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-muted">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text focus:border-brand-500 focus:outline-none"
      />
    </label>
  );
}

export function LabeledSelect({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-muted">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text focus:border-brand-500 focus:outline-none"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

// For a multi-value field like "chunk sizes to sweep": comma-separated numbers.
export function LabeledMultiNumberInput({ label, value, onChange, placeholder }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-muted">{label}</span>
      <input
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-text focus:border-brand-500 focus:outline-none"
      />
      <span className="mt-0.5 block text-[11px] text-muted">Comma-separated, e.g. 200,400</span>
    </label>
  );
}

export function parseNumberList(s) {
  return s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean)
    .map(Number)
    .filter((n) => !Number.isNaN(n));
}
