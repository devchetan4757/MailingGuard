/**
 * Shared page header — integrator / design lead owned.
 * PROPS CONTRACT: {
 *   title: string, subtitle?: string,
 *   actionLabel?: string, onAction?: () => void, actionHref?: string
 * }
 * UI_DESIGN_SPEC.md §3: the page's real title ("Hello, [Analyst Name]"
 * style greeting), primary action button aligned right — same position
 * every page.
 */

import { Link } from "react-router-dom";

export default function PageHeader({ title, subtitle, actionLabel, onAction, actionHref }) {
  return (
    <div className="flex items-start justify-between mb-8">
      <div>
        <h1 className="font-semibold text-[38px] text-text-primary leading-tight">{title}</h1>
        {subtitle && <p className="text-base text-text-secondary mt-2">{subtitle}</p>}
      </div>

      {actionLabel && actionHref && (
        <Link
          to={actionHref}
          className="shrink-0 bg-accent text-bg-canvas text-base font-medium px-6 py-3.5 rounded-[10px] hover:brightness-95 transition"
        >
          {actionLabel}
        </Link>
      )}
      {actionLabel && onAction && !actionHref && (
        <button
          onClick={onAction}
          className="shrink-0 bg-accent text-bg-canvas text-base font-medium px-6 py-3.5 rounded-[10px] hover:brightness-95 transition"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
