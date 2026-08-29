/**
 * Shared empty state — integrator owned.
 * PROPS CONTRACT: { title: string, body: string, actionLabel?: string, onAction?: () => void }
 */

export default function EmptyState({ title, body, actionLabel, onAction }) {
  return (
    <div className="text-center py-16 text-text-secondary bg-bg-card border border-border-subtle rounded-[16px]">
      <p className="font-semibold text-lg text-text-primary">{title}</p>
      <p className="text-sm mt-2">{body}</p>
      {actionLabel && (
        <button onClick={onAction} className="mt-4 text-sm text-accent hover:underline">
          {actionLabel}
        </button>
      )}
    </div>
  );
}
