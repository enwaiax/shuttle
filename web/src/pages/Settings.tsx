import { useEffect, useState } from "react";
import { useSettings, useUpdateSettings } from "../api/client";
import type { SettingsUpdate } from "../types";

const inputCls =
  "w-full rounded-md border border-[#222] bg-[#0e0e0e] px-3 py-2 text-[13px] text-[#ededed] outline-none tabular-nums focus:border-[#444]";

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

  function Field({ label, field, suffix }: { label: string; field: keyof SettingsUpdate; suffix?: string }) {
    return (
      <div>
        <label className="mb-1 block text-[11px] font-medium text-[#666]">
          {label}
          {suffix && <span className="ml-1 text-[#444]">({suffix})</span>}
        </label>
        <input
          type="number"
          value={form[field] ?? ""}
          onChange={(e) => handleChange(field, e.target.value)}
          className={inputCls}
        />
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-[15px] font-medium text-[#ededed]">Settings</h1>
      <p className="mt-1 text-[13px] text-[#555]">Connection pool and cleanup configuration</p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-8">
        <section>
          <h2 className="text-[13px] font-medium text-[#999]">Connection Pool</h2>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Field label="Max Total" field="pool_max_total" />
            <Field label="Max Per Node" field="pool_max_per_node" />
            <Field label="Idle Timeout" field="pool_idle_timeout" suffix="sec" />
            <Field label="Max Lifetime" field="pool_max_lifetime" suffix="sec" />
            <Field label="Queue Size" field="pool_queue_size" />
          </div>
        </section>

        <section>
          <h2 className="text-[13px] font-medium text-[#999]">Cleanup Policy</h2>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Field label="Command Logs" field="cleanup_command_logs_days" suffix="days" />
            <Field label="Closed Sessions" field="cleanup_closed_sessions_days" suffix="days" />
          </div>
        </section>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={update.isPending}
            className="rounded-md bg-[#ededed] px-4 py-1.5 text-[13px] font-medium text-[#0a0a0a] hover:opacity-90 disabled:opacity-30"
          >
            {update.isPending ? "Saving…" : "Save"}
          </button>
          {saved && <span className="text-[12px] text-[#30d158]">Saved</span>}
        </div>
      </form>
    </div>
  );
}
