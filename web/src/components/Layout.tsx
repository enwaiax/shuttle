import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  const { pathname } = useLocation();
  const isActivity = pathname.startsWith("/activity");

  return (
    <div className="flex h-screen overflow-hidden bg-[#0a0a0a]">
      <Sidebar />
      <main
        className={`flex-1 overflow-hidden ${
          isActivity ? "" : "overflow-y-auto bg-[#0a0a0a] p-8"
        }`}
      >
        <Outlet />
      </main>
    </div>
  );
}
