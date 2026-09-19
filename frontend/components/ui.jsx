export function Spinner() {
  return (
    <div className="flex items-center gap-2 text-sm text-muted">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      Running…
    </div>
  );
}

export function ErrorBanner({ message }) {
  return (
    <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{message}</div>
  );
}

export function Button({ children, onClick, disabled, variant = "primary", type = "button" }) {
  const base =
    "rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const styles =
    variant === "primary"
      ? "bg-brand-600 text-white hover:bg-brand-700"
      : "border border-border bg-surface text-text hover:bg-surfaceHover";
  return (
    <button type={type} className={`${base} ${styles}`} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}
