export default function PhasePlaceholder({ title, phase, description }) {
  return (
    <div className="mx-auto max-w-2xl px-8 py-10">
      <h1 className="text-lg font-medium text-text">{title}</h1>
      <p className="mt-1 text-sm text-muted">{description}</p>
      <div className="mt-6 rounded-md border border-dashed border-border p-6 text-sm text-muted">
        Not built yet — this page ships in <span className="text-accent">{phase}</span> of the
        roadmap.
      </div>
    </div>
  );
}
