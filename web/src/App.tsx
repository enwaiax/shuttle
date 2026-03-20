import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Nodes from "./pages/Nodes";
import Rules from "./pages/Rules";
import Sessions from "./pages/Sessions";
import SessionDetail from "./pages/SessionDetail";
import Logs from "./pages/Logs";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/nodes" element={<Nodes />} />
        <Route path="/rules" element={<Rules />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/sessions/:id" element={<SessionDetail />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
