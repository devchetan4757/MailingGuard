// src/components/layout/TopBar.jsx

import {
  ChevronLeft,
  ChevronRight,
  CircleHelp,
} from "lucide-react";

function todayLabel() {
  return new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

export default function TopBar() {
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

        <span className="reference-product-title">
          Dashboard
        </span>
      </div>

      <div className="reference-topbar-actions">
        <div className="reference-top-date">
          <button
            type="button"
            aria-label="Previous date"
          >
            <ChevronLeft size={15} />
          </button>

          <span>{todayLabel()}</span>

          <button
            type="button"
            aria-label="Next date"
          >
            <ChevronRight size={15} />
          </button>
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
