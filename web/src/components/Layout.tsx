import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  const { pathname } = useLocation();
  const isConsole = pathname.startsWith("/activity");

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950">
      <Sidebar />
      <main
        className={`flex-1 overflow-hidden ${
          isConsole ? "" : "overflow-y-auto bg-gray-50 p-8"
        }`}
      >
        <Outlet />
      </main>
    </div>
  );
}
