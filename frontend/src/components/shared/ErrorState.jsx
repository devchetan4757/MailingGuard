/**
 * Shared error state — integrator owned.
 * PROPS CONTRACT: { message: string }
 * Per UI_DESIGN_SPEC.md principles: a clear, friendly message, never a
 * blank page or console error. Uses severity-red at low opacity.
 */

export default function ErrorState({ message }) {
  return (
    <div className="border border-severity-red/40 bg-severity-red/10 text-severity-red text-sm rounded-[16px] p-4">
      {message}
    </div>
  );
}
