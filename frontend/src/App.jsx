// src/App.jsx

import { BrowserRouter } from "react-router-dom";
import Sidebar from "./components/layout/SideBar";
import TopBar from "./components/layout/TopBar";
import AppRoutes from "./router";
import { CaseProvider } from "./context/CaseContext";

function App() {
  return (
    <BrowserRouter>
      <CaseProvider>
        <div className="reference-app-shell">
          <TopBar />

          <div className="reference-body">
            <Sidebar />

            <div className="reference-content">
              <AppRoutes />
            </div>
          </div>
        </div>
      </CaseProvider>
    </BrowserRouter>
  );
}

export default App;
