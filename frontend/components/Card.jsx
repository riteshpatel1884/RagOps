export default function Card({ title, description, children, className = "" }) {
  return (
    <div className={`rounded-xl border border-border bg-surface p-6 shadow-card ${className}`}>
      {title && (
        <div className="mb-4">
          <h2 className="text-base font-semibold text-text">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-muted">{description}</p>}
        </div>
      )}
      {children}
    </div>
  );
}
