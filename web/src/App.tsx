import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import { getToken } from "./api/client";
import { AppProvider } from "./hooks/AppContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Overview from "./pages/Overview";
import Activity from "./pages/Activity";
import Rules from "./pages/Rules";
import Settings from "./pages/Settings";

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  return (
    <AppProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Overview />} />
          <Route path="/nodes/:nodeId" element={<Activity />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </AppProvider>
  );
}
