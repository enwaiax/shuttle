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
      setError("Cannot reach server");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
      {/* Subtle grid texture */}
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.1) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
        }}
      />

      <div className="relative w-full max-w-[360px] px-6">
        {/* Logo mark */}
        <div className="mb-10 flex flex-col items-center">
          <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-lg border border-[#222] bg-[#111]">
            <span
              className="text-[15px] font-semibold text-[#ededed]"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              S
            </span>
          </div>
          <h1 className="text-[15px] font-medium tracking-[-0.01em] text-[#ededed]">
            Shuttle
          </h1>
          <p className="mt-2 text-[13px] leading-relaxed text-[#666]">
            Paste the token from your terminal
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="relative">
            <input
              type="password"
              value={token}
              onChange={(e) => setTokenValue(e.target.value)}
              placeholder="shuttle-xxxxxxxxxxxx"
              autoFocus
              required
              className="h-10 w-full rounded-lg border border-[#222] bg-[#0f0f0f] px-3 text-[13px] text-[#ededed] outline-none transition-colors placeholder:text-[#333] focus:border-[#444]"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            />
          </div>

          {error && (
            <p className="mt-3 text-center text-[12px] text-[#f04] ">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !token}
            className="mt-4 h-10 w-full rounded-lg bg-[#ededed] text-[13px] font-medium text-[#0a0a0a] transition-opacity hover:opacity-90 disabled:opacity-30"
          >
            {loading ? "Verifying…" : "Connect"}
          </button>
        </form>

        <p className="mt-8 text-center text-[11px] text-[#444]">
          <code className="rounded border border-[#1a1a1a] bg-[#111] px-1.5 py-0.5 text-[#555]">
            shuttle serve
          </code>
          {" "}to start
        </p>
      </div>
    </div>
  );
}
