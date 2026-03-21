import { useState, useCallback } from "react";

export interface RecentNode {
  id: string;
  name: string;
  status: string;
}

const STORAGE_KEY = "shuttle_recent_nodes";
const MAX_RECENT = 5;

function load(): RecentNode[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.slice(0, MAX_RECENT);
  } catch {
    return [];
  }
}

function save(nodes: RecentNode[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nodes.slice(0, MAX_RECENT)));
}

export function useRecentNodes() {
  const [recent, setRecent] = useState<RecentNode[]>(load);

  const track = useCallback((node: RecentNode) => {
    setRecent((prev) => {
      const existing = prev.find((n) => n.id === node.id);
      if (existing) {
        if (existing.status === node.status && existing.name === node.name) return prev;
        const updated = prev.map((n) => (n.id === node.id ? node : n));
        save(updated);
        return updated;
      }
      const next = [node, ...prev].slice(0, MAX_RECENT);
      save(next);
      return next;
    });
  }, []);

  return { recent, track } as const;
}
