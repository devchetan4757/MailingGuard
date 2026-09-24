// src/components/layout/TopBar.jsx

import { useEffect, useState } from "react";
import { useLocation, matchPath } from "react-router-dom";
import { CalendarClock, CircleHelp } from "lucide-react";
import { useCaseContext } from "../../context/CaseContext";

// Maps each route to the title shown in the topbar. Keep labels aligned
// with SideBar.jsx so the active nav item and the topbar always agree.
const ROUTES = [
  { pattern: "/", title: "Dashboard" },
  { pattern: "/upload", title: "Upload & Parse" },
  { pattern: "/gmail", title: "Gmail Integration" },
  { pattern: "/analyze", title: "AI Deep Analysis" },
  { pattern: "/origin", title: "Origin Analysis" },
  { pattern: "/reports", title: "Reports" },
  { pattern: "/results/:caseId", title: "Case Results" },
  { pattern: "/deep-analysis/report", title: "Deep Analysis Report" },
  { pattern: "/deep-analysis/source", title: "Page Source" },
];

function getPageInfo(pathname) {
  for (const route of ROUTES) {
    const match = matchPath({ path: route.pattern, end: true }, pathname);
    if (match) {
      return { title: route.title, caseId: match.params?.caseId };
    }
  }
  return { title: "MailGuard" };
}

const CASE_SCOPED_TITLES = new Set([
  "Case Results",
  "Deep Analysis Report",
  "Page Source",
]);

export default function TopBar() {
  const location = useLocation();
  const { currentCase } = useCaseContext();
  const [now, setNow] = useState(new Date());

  // Keep the clock live without re-rendering the whole app too often.
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(id);
  }, []);

  const { title, caseId } = getPageInfo(location.pathname);
  const activeCaseId = caseId || currentCase?.caseId;
  const showCaseSubtitle = activeCaseId && CASE_SCOPED_TITLES.has(title);

  const dateLabel = now.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const timeLabel = now.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <header className="reference-topbar">
      <div className="reference-topbar-brand">
        <div
          className="reference-logo"
          aria-label="ThreadDetect"
        >
          <span />
          <span />
          <span />
        </div>

        <div className="reference-topbar-titles">
          <span className="reference-product-title">{title}</span>
          {showCaseSubtitle && (
            <span className="reference-page-subtitle">
              Case #{activeCaseId}
            </span>
          )}
        </div>
      </div>

      <div className="reference-topbar-actions">
        <div className="reference-top-date" title={now.toLocaleString()}>
          <CalendarClock size={15} />
          <span>
            {dateLabel} · {timeLabel}
          </span>
        </div>

        <button
          className="reference-help"
          type="button"
          aria-label="Help"
        >
          <CircleHelp size={15} />
        </button>
      </div>
    </header>
  );
}
