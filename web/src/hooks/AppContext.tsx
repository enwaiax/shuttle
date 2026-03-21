import { createContext, useContext, type ReactNode } from "react";
import { useTheme } from "./useTheme";
import { useRecentNodes, type RecentNode } from "./useRecentNodes";

interface AppContextValue {
  theme: "dark" | "light";
  toggleTheme: () => void;
  recentNodes: RecentNode[];
  trackNode: (node: RecentNode) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme();
  const { recent, track } = useRecentNodes();

  return (
    <AppContext.Provider
      value={{ theme, toggleTheme: toggle, recentNodes: recent, trackNode: track }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
