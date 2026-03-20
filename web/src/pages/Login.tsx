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
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600">
            <span className="text-lg font-bold text-white">S</span>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Shuttle</h1>
          <p className="mt-1 text-sm text-gray-500">
            Enter the API token shown in your terminal
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="password"
              value={token}
              onChange={(e) => setTokenValue(e.target.value)}
              placeholder="Paste API token here"
              className="w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              autoFocus
              required
            />
          </div>
          {error && (
            <p className="text-center text-xs text-red-500">{error}</p>
          )}
          <button
            type="submit"
            disabled={loading || !token}
            className="w-full rounded-lg bg-blue-500 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? "Verifying..." : "Connect"}
          </button>
        </form>
      </div>
    </div>
  );
}
