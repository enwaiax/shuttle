import { type ReactNode } from "react";

export interface Column<T> {
  key: string;
  label: string;
  render?: (row: T) => ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: keyof T;
}

export default function DataTable<T>({
  columns,
  data,
  keyField,
}: DataTableProps<T>) {
  return (
    <div className="overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)]">
      <table className="min-w-full">
        <thead>
          <tr className="border-b border-[var(--border-subtle)]">
            {columns.map((col) => (
              <th
                key={col.key}
                className="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--text-quaternary)]"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={String(row[keyField])}
              className="border-b border-[var(--border-subtle)] transition-colors duration-150 last:border-b-0 hover:bg-[var(--bg-tertiary)]"
              style={{ animationDelay: `${i * 30}ms` }}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className="whitespace-nowrap px-5 py-3 text-[13px] text-[var(--text-secondary)]"
                >
                  {col.render
                    ? col.render(row)
                    : String((row as Record<string, unknown>)[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
