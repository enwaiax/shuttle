import { useEffect, useState } from "react";
import { useSettings, useUpdateSettings } from "../api/client";
import type { SettingsUpdate } from "../types";
import { Settings as SettingsIcon, Check } from "lucide-react";

const inputCls =
  "focus-ring w-full rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-[13px] tabular-nums text-[var(--text-primary)] outline-none transition-all duration-200 hover:border-[var(--border-strong)]";

export default function Settings() {
  const { data: settings } = useSettings();
  const update = useUpdateSettings();
  const [form, setForm] = useState<SettingsUpdate>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (settings) {
      setForm({
        pool_max_total: settings.pool_max_total,
        pool_max_per_node: settings.pool_max_per_node,
        pool_idle_timeout: settings.pool_idle_timeout,
        pool_max_lifetime: settings.pool_max_lifetime,
        pool_queue_size: settings.pool_queue_size,
        cleanup_command_logs_days: settings.cleanup_command_logs_days,
        cleanup_closed_sessions_days: settings.cleanup_closed_sessions_days,
      });
    }
  }, [settings]);

  function handleChange(key: keyof SettingsUpdate, value: string) {
    setForm((prev) => ({ ...prev, [key]: Number(value) }));
    setSaved(false);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    update.mutate(form, { onSuccess: () => setSaved(true) });
  }

  function Field({
    label,
    field,
    suffix,
  }: {
    label: string;
    field: keyof SettingsUpdate;
    suffix?: string;
  }) {
    return (
      <div>
        <label className="mb-2 block text-[12px] font-medium text-[var(--text-secondary)]">
          {label}
          {suffix && (
            <span className="ml-1.5 text-[var(--text-quaternary)]">({suffix})</span>
          )}
        </label>
        <input
          type="number"
          value={form[field] ?? ""}
          onChange={(e) => handleChange(field, e.target.value)}
          className={inputCls}
          style={{ fontFamily: "var(--font-mono)" }}
        />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-black p-8">
      <div className="max-w-2xl">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--green-subtle)]">
            <SettingsIcon size={15} className="text-[var(--green)]" strokeWidth={1.8} />
          </div>
          <div>
            <h1 className="text-[17px] font-bold tracking-[-0.02em] text-[var(--text-primary)]">
              Settings
            </h1>
            <p className="text-[12px] text-[var(--text-tertiary)]">
              Connection pool and cleanup configuration
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-8">
          <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6">
            <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">
              Connection Pool
            </h2>
            <p className="mt-1 text-[12px] text-[var(--text-quaternary)]">
              Configure SSH connection pool behavior
            </p>
            <div className="mt-5 grid grid-cols-2 gap-4">
              <Field label="Max Total" field="pool_max_total" />
              <Field label="Max Per Node" field="pool_max_per_node" />
              <Field label="Idle Timeout" field="pool_idle_timeout" suffix="sec" />
              <Field label="Max Lifetime" field="pool_max_lifetime" suffix="sec" />
              <Field label="Queue Size" field="pool_queue_size" />
            </div>
          </section>

          <section className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6">
            <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">
              Cleanup Policy
            </h2>
            <p className="mt-1 text-[12px] text-[var(--text-quaternary)]">
              Automatically clean up old data
            </p>
            <div className="mt-5 grid grid-cols-2 gap-4">
              <Field
                label="Command Logs"
                field="cleanup_command_logs_days"
                suffix="days"
              />
              <Field
                label="Closed Sessions"
                field="cleanup_closed_sessions_days"
                suffix="days"
              />
            </div>
          </section>

          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={update.isPending}
              className="rounded-xl bg-[var(--green)] px-6 py-2.5 text-[13px] font-semibold text-black transition-all duration-200 hover:bg-[var(--green-light)] hover:shadow-[0_0_24px_rgba(118,185,0,0.3)] disabled:opacity-30"
            >
              {update.isPending ? "Saving…" : "Save Changes"}
            </button>
            {saved && (
              <span className="animate-slide-up flex items-center gap-1.5 text-[12px] font-medium text-[var(--green)]">
                <Check size={14} />
                Saved successfully
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
