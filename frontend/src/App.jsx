import React from "react";
import { Routes, Route } from "react-router-dom";
import TopBar from "./components/TopBar.jsx";

import RoutersPage from "./pages/Routers.jsx";
import HistoryPage from "./pages/History.jsx";
import CheckupsPage from "./pages/Checkups.jsx";
import CommandsPage from "./pages/Commands.jsx";
import SettingsPage from "./pages/Settings.jsx";

export default function App() {
  return (
    <div className="min-h-[100vh] flex flex-col bg-gray-950 text-gray-100">
      <TopBar />
      <main className="flex-1 overflow-auto p-[18px]">
        <Routes>
          <Route path="/" element={<RoutersPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/checkups" element={<CheckupsPage />} />
          <Route path="/commands" element={<CommandsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
