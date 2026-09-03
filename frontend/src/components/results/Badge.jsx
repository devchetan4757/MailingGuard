/**
 * Epic 2 owner — this is the project's shared SeverityPill.
 * PROPS CONTRACT: { severity: "green" | "yellow" | "red", children: ReactNode }
 * Colour logic is fixed project-wide: green=low, yellow=medium, red=high
 * (UI_DESIGN_SPEC.md section 2). Keep the mapping identical anywhere this shared badge is used.
 */

const SEVERITY_CLASSES = {
  green: "bg-severity-green/15 text-severity-green",
  yellow: "bg-severity-yellow/15 text-severity-yellow",
  red: "bg-severity-red/15 text-severity-red",
};

export default function Badge({ severity, children }) {
  return (
    <span className={`text-xs font-mono px-3 py-1 rounded-full whitespace-nowrap ${SEVERITY_CLASSES[severity]}`}>
      {children}
    </span>
  );
}
