import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import { getToken } from "./api/client";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Overview from "./pages/Overview";
import Activity from "./pages/Activity";
import Nodes from "./pages/Nodes";
import Rules from "./pages/Rules";
import Settings from "./pages/Settings";

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/activity/:nodeId" element={<Activity />} />
        <Route path="/nodes" element={<Nodes />} />
        <Route path="/rules" element={<Rules />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
