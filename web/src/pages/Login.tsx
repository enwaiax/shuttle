import { useState } from "react";
import { setToken } from "../api/client";

interface Props {
  onLogin: () => void;
}

export default function Login({ onLogin }: Props) {
  const [token, setTokenValue] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/stats", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setToken(token);
        onLogin();
      } else {
        setError("Invalid token");
      }
    } catch {
      setError("Cannot connect to server");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-500">
            <span className="text-lg font-bold text-zinc-900">S</span>
          </div>
          <h1 className="text-xl font-semibold text-zinc-100">Shuttle</h1>
          <p className="mt-2 text-sm text-zinc-500">
            Paste the API token from your terminal
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="password"
              value={token}
              onChange={(e) => setTokenValue(e.target.value)}
              placeholder="API token"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2.5 font-mono text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20"
              autoFocus
              required
            />
          </div>
          {error && (
            <p className="text-center text-xs text-red-400">{error}</p>
          )}
          <button
            type="submit"
            disabled={loading || !token}
            className="w-full rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-medium text-zinc-900 hover:bg-emerald-400 disabled:opacity-40"
          >
            {loading ? "Verifying…" : "Connect"}
          </button>
        </form>

        <p className="mt-6 text-center text-[11px] text-zinc-700">
          Run <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-zinc-400">shuttle serve</code> to get your token
        </p>
      </div>
    </div>
  );
}
