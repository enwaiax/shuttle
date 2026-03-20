import { useEffect, useState } from "react";
import { useSettings, useUpdateSettings } from "../api/client";
import type { SettingsUpdate } from "../types";

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
    update.mutate(form, {
      onSuccess: () => setSaved(true),
    });
  }

  const inputCls =
    "w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

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
        <label className="mb-1.5 block text-sm font-medium text-gray-700">
          {label}
          {suffix && (
            <span className="ml-1 font-normal text-gray-400">({suffix})</span>
          )}
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
      <h1 className="text-lg font-semibold text-gray-900">Settings</h1>
      <p className="mt-1 text-sm text-gray-500">
        Configure connection pool and cleanup policies.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-8">
        {/* Connection Pool */}
        <section>
          <h2 className="text-sm font-semibold text-gray-900">
            Connection Pool
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Max Total" field="pool_max_total" />
            <Field label="Max Per Node" field="pool_max_per_node" />
            <Field
              label="Idle Timeout"
              field="pool_idle_timeout"
              suffix="seconds"
            />
            <Field
              label="Max Lifetime"
              field="pool_max_lifetime"
              suffix="seconds"
            />
            <Field label="Queue Size" field="pool_queue_size" />
          </div>
        </section>

        {/* Cleanup Policy */}
        <section>
          <h2 className="text-sm font-semibold text-gray-900">
            Cleanup Policy
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
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

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={update.isPending}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {update.isPending ? "Saving..." : "Save Settings"}
          </button>
          {saved && (
            <span className="text-sm text-green-600">Settings saved.</span>
          )}
        </div>
      </form>
    </div>
  );
}
