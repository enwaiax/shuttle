import { Server, Terminal, ScrollText } from "lucide-react";
import { useStats } from "../api/client";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: number | undefined;
  icon: LucideIcon;
  color: string;
  iconBg: string;
}

function StatCard({ label, value, icon: Icon, color, iconBg }: StatCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-4">
        <div className={`rounded-lg p-2.5 ${iconBg}`}>
          <Icon size={20} className={color} strokeWidth={1.8} />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="mt-0.5 text-2xl font-semibold tracking-tight text-gray-900">
            {value ?? "--"}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data: stats } = useStats();

  return (
    <div>
      <h1 className="text-lg font-semibold text-gray-900">Dashboard</h1>
      <p className="mt-1 text-sm text-gray-500">
        Overview of your Shuttle environment.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="SSH Nodes"
          value={stats?.node_count}
          icon={Server}
          color="text-blue-600"
          iconBg="bg-blue-50"
        />
        <StatCard
          label="Active Sessions"
          value={stats?.active_sessions}
          icon={Terminal}
          color="text-emerald-600"
          iconBg="bg-emerald-50"
        />
        <StatCard
          label="Total Commands"
          value={stats?.total_commands}
          icon={ScrollText}
          color="text-indigo-600"
          iconBg="bg-indigo-50"
        />
      </div>
    </div>
  );
}
