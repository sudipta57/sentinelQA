type StatCardColor = "default" | "green" | "red" | "purple";

interface StatCardProps {
  label: string;
  value: number | string;
  color?: StatCardColor;
}

const VALUE_COLOR_CLASS: Record<StatCardColor, string> = {
  default: "text-white",
  green: "text-green-400",
  red: "text-red-400",
  purple: "text-purple-400",
};

export default function StatCard({ label, value, color = "default" }: StatCardProps): JSX.Element {
  return (
    <div className="rounded-lg bg-gray-900 p-4">
      <div className={`text-2xl font-bold ${VALUE_COLOR_CLASS[color]}`}>{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-gray-400">{label}</div>
    </div>
  );
}
