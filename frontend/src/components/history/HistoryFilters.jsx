/**
 * Epic 4 owner.
 * PROPS CONTRACT: { search: string, onSearchChange: (v: string) => void,
 *   severityFilter: string, onSeverityChange: (v: string) => void }
 */

export default function HistoryFilters({ search, onSearchChange, severityFilter, onSeverityChange }) {
  return (
    <div className="flex gap-2">
      <input
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search sender or case ID"
        className="text-sm border border-graphite/30 rounded-sm px-3 py-1"
      />
      <select
        value={severityFilter}
        onChange={(e) => onSeverityChange(e.target.value)}
        className="text-sm border border-graphite/30 rounded-sm px-3 py-1"
      >
        <option value="">All severities</option>
        <option value="red">High</option>
        <option value="yellow">Medium</option>
        <option value="green">Low</option>
      </select>
    </div>
  );
}
