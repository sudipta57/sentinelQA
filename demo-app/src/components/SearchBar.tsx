interface SearchBarProps {
  query: string;
  onChange: (value: string) => void;
}

export function SearchBar({ query, onChange }: SearchBarProps): JSX.Element {
  return (
    <input
      type="text"
      value={query}
      onChange={(event) => onChange(event.target.value)}
      placeholder="Search by name or email..."
      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-500 transition focus:ring"
    />
  );
}
