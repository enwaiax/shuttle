import { useEffect, useState, useRef } from "react";
import { useSettings, useUpdateSettings, exportData, importData } from "../api/client";
import type { SettingsUpdate } from "../types";
import { Settings as SettingsIcon, Check, Download, Upload, Database, AlertCircle } from "lucide-react";

const inputCls =
  "focus-ring w-full rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-[13px] tabular-nums text-[var(--text-primary)] outline-none transition-all duration-200 hover:border-[var(--border-strong)]";

export default function Settings() {
  const { data: settings } = useSettings();
  const update = useUpdateSettings();
  const [form, setForm] = useState<SettingsUpdate>({});
  const [saved, setSaved] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [dataMsg, setDataMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    <div className="h-full overflow-y-auto bg-[var(--bg-primary)] p-8">
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

        <section className="mt-8 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)] p-6">
          <div className="flex items-center gap-2">
            <Database size={15} className="text-[var(--text-quaternary)]" />
            <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">
              Data Management
            </h2>
          </div>
          <p className="mt-1 text-[12px] text-[var(--text-quaternary)]">
            Export or import your configuration data as JSON
          </p>

          <div className="mt-5 flex items-center gap-3">
            <button
              type="button"
              disabled={exporting}
              onClick={async () => {
                setExporting(true);
                setDataMsg(null);
                try {
                  const blob = await exportData();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `shuttle-export-${new Date().toISOString().slice(0, 10)}.json`;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                  URL.revokeObjectURL(url);
                  setDataMsg({ type: "success", text: "Export downloaded successfully" });
                } catch (err) {
                  setDataMsg({ type: "error", text: err instanceof Error ? err.message : "Export failed" });
                } finally {
                  setExporting(false);
                }
              }}
              className="inline-flex items-center gap-2 rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-[13px] font-medium text-[var(--text-secondary)] transition-all duration-200 hover:bg-[var(--bg-hover)] disabled:opacity-30"
            >
              <Download size={14} strokeWidth={1.8} />
              {exporting ? "Exporting…" : "Export"}
            </button>

            <button
              type="button"
              disabled={importing}
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-2 rounded-xl border border-[var(--border-default)] bg-[var(--bg-tertiary)] px-4 py-2.5 text-[13px] font-medium text-[var(--text-secondary)] transition-all duration-200 hover:bg-[var(--bg-hover)] disabled:opacity-30"
            >
              <Upload size={14} strokeWidth={1.8} />
              {importing ? "Importing…" : "Import"}
            </button>

            <input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              className="hidden"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setImporting(true);
                setDataMsg(null);
                try {
                  const text = await file.text();
                  const json = JSON.parse(text);
                  const result = await importData(json);
                  setDataMsg({ type: "success", text: result.message || "Import completed successfully" });
                } catch (err) {
                  setDataMsg({
                    type: "error",
                    text: err instanceof Error ? err.message : "Import failed",
                  });
                } finally {
                  setImporting(false);
                  // Reset file input so the same file can be re-selected
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }
              }}
            />
          </div>

          {dataMsg && (
            <div
              className={`mt-4 flex items-center gap-2 rounded-lg px-4 py-2.5 text-[12px] font-medium ${
                dataMsg.type === "success"
                  ? "bg-[var(--green-subtle)] text-[var(--green)]"
                  : "bg-[var(--red-subtle)] text-[var(--red)]"
              }`}
            >
              {dataMsg.type === "success" ? <Check size={14} /> : <AlertCircle size={14} />}
              {dataMsg.text}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
