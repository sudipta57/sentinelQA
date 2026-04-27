type StatCardColor = "default" | "green" | "red" | "purple";

interface StatCardProps {
  label: string;
  value: number | string;
  color?: StatCardColor;
}

const VALUE_COLOR_CLASS: Record<StatCardColor, string> = {
  default: "text-gray-900",
  green: "text-emerald-600",
  red: "text-rose-600",
  purple: "text-gray-900", // Fallback to default
};

export default function StatCard({ label, value, color = "default" }: StatCardProps): JSX.Element {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-none">
      <div className={`text-2xl font-bold ${VALUE_COLOR_CLASS[color]}`}>{value}</div>
      <div className="mt-1 text-xs font-medium uppercase tracking-wide text-gray-400">{label}</div>
    </div>
  );
}
