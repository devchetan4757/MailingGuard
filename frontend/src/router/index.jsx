import { Routes, Route } from "react-router-dom";
import DashboardPage from "../pages/DashboardPage";
import UploadPage from "../pages/UploadPage";
import AnalysisPage from "../pages/AnalysisPage";
import OriginAnalysisPage from "../pages/OriginAnalysisPage";
import ReportsPage from "../pages/ReportsPage";
import ResultsPage from "../pages/ResultsPage";
import GmailPage from "../pages/GmailPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={<DashboardPage />}
      />

      <Route
        path="/upload"
        element={<UploadPage />}
      />

      <Route
        path="/analyze"
        element={<AnalysisPage />}
      />

      <Route
        path="/origin"
        element={<OriginAnalysisPage />}
      />

      <Route
        path="/reports"
        element={<ReportsPage />}
      />

      <Route
        path="/results/:caseId"
        element={<ResultsPage />}
      />

      <Route
        path="/gmail"
        element={<GmailPage />}
      />
    </Routes>
  );
}
