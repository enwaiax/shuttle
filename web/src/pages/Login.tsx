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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black">
      {/* Grid background — NVIDIA style */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(118, 185, 0, 0.3) 1px, transparent 1px),
            linear-gradient(90deg, rgba(118, 185, 0, 0.3) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
        }}
      />

      {/* Radial green glow from center */}
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full"
        style={{
          background:
            "radial-gradient(circle, rgba(118, 185, 0, 0.06) 0%, transparent 70%)",
        }}
      />

      {/* Login card */}
      <div className="animate-slide-up relative z-10 w-full max-w-[380px] px-6">
        {/* Logo */}
        <div className="mb-12 flex flex-col items-center">
          <div className="glow-green-sm mb-6 flex h-12 w-12 items-center justify-center rounded-xl border border-[var(--green)]/20 bg-[var(--green-subtle)]">
            <span
              className="text-[18px] font-bold text-[var(--green)]"
              style={{ fontFamily: "var(--font-mono)" }}
            >
              S
            </span>
          </div>
          <h1 className="text-[22px] font-bold tracking-[-0.03em] text-[var(--text-primary)]">
            Shuttle
          </h1>
          <p className="mt-2 text-[13px] text-[var(--text-tertiary)]">
            SSH Gateway for AI Assistants
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-[12px] font-medium text-[var(--text-secondary)]">
              API Token
            </label>
            <input
              type="password"
              value={token}
              onChange={(e) => setTokenValue(e.target.value)}
              placeholder="shuttle-xxxxxxxxxxxx"
              autoFocus
              required
              className="focus-ring h-11 w-full rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 text-[13px] text-[var(--text-primary)] outline-none transition-all duration-200 placeholder:text-[var(--text-muted)] hover:border-[var(--border-strong)]"
              style={{ fontFamily: "var(--font-mono)" }}
            />
          </div>

          {error && (
            <div className="animate-slide-up rounded-lg bg-[var(--red-subtle)] px-4 py-2.5 text-[12px] font-medium text-[var(--red)]">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !token}
            className="h-11 w-full rounded-xl bg-[var(--green)] text-[14px] font-semibold text-black transition-all duration-200 hover:bg-[var(--green-light)] hover:shadow-[0_0_24px_rgba(118,185,0,0.3)] disabled:opacity-30 disabled:hover:shadow-none"
          >
            {loading ? "Verifying…" : "Connect"}
          </button>
        </form>

        <p className="mt-10 text-center text-[12px] text-[var(--text-quaternary)]">
          Run{" "}
          <code className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-2 py-0.5 text-[11px] text-[var(--text-tertiary)]">
            shuttle serve
          </code>{" "}
          to start the server
        </p>
      </div>
    </div>
  );
}
