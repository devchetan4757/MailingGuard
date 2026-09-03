/**
 * Shared modal shell — integrator owned.
 * PROPS CONTRACT: { isOpen: boolean, onClose: () => void, children: ReactNode }
 */

export default function Modal({ isOpen, onClose, children }) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-bg-card border border-border-subtle rounded-[16px] p-6 max-w-md w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
