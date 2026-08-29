// src/components/layout/TopBar.jsx

import {
  CircleHelp,
} from "lucide-react";

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
