/**
 * Shared case context — integrator owned.
 * Holds the currently-open case so ResultsPage and its child components
 * (owned by different people) can all read it without prop drilling.
 */

import { createContext, useContext, useState } from "react";

const CaseContext = createContext(null);

export function CaseProvider({ children }) {
  const [currentCase, setCurrentCase] = useState(null);
  return (
    <CaseContext.Provider value={{ currentCase, setCurrentCase }}>
      {children}
    </CaseContext.Provider>
  );
}

export function useCaseContext() {
  const ctx = useContext(CaseContext);
  if (!ctx) throw new Error("useCaseContext must be used inside CaseProvider");
  return ctx;
}
