// src/components/layout/SideBar.jsx

import { NavLink } from "react-router-dom";
import {
  BrainCircuit,
  FileText,
  LayoutGrid,
  Radar,
  Mail,
} from "lucide-react";

const NAV_ITEMS = [
  {
    to: "/",
    icon: LayoutGrid,
    label: "Dashboard",
    end: true,
  },
  {
  to: "/gmail",
  icon: Mail,
  label: "Gmail Integration",
},
  {
    to: "/analyze",
    icon: BrainCircuit,
    label: "AI Deep Analysis",
  },
  {
    to: "/origin",
    icon: Radar,
    label: "Origin Analysis",
  },
  {
    to: "/reports",
    icon: FileText,
    label: "Reports",
  },
];

export default function Sidebar() {
  return (
    <aside className="reference-sidebar">
      <nav className="reference-side-nav">
        {NAV_ITEMS.map(
          ({
            to,
            icon: Icon,
            label,
            end,
          }) => (
            <NavLink
              key={label}
              to={to}
              end={end}
              title={label}
              className={({ isActive }) =>
                `reference-side-link ${
                  isActive ? "is-active" : ""
                }`
              }
            >
              <Icon
                size={19}
                strokeWidth={1.8}
              />
            </NavLink>
          )
        )}
      </nav>
    </aside>
  );
}
