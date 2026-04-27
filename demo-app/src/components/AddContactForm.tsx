import { useState } from "react";
import type { Contact, ContactCategory } from "../types";

interface AddContactFormProps {
  onAdd: (contact: Omit<Contact, "id">) => void;
}

const defaultForm = {
  name: "",
  email: "",
  phone: "",
  category: "Friend" as ContactCategory,
};

export function AddContactForm({ onAdd }: AddContactFormProps): JSX.Element {
  const [formData, setFormData] = useState(defaultForm);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    onAdd(formData);
    setFormData(defaultForm);
  };

  return (
    <form onSubmit={handleSubmit} className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
      <input
        type="text"
        value={formData.name}
        onChange={(event) => setFormData((prev) => ({ ...prev, name: event.target.value }))}
        placeholder="Name"
        className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-500 transition focus:ring"
      />
      <input
        type="email"
        value={formData.email}
        onChange={(event) => setFormData((prev) => ({ ...prev, email: event.target.value }))}
        placeholder="Email"
        className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-500 transition focus:ring"
      />
      <input
        type="tel"
        value={formData.phone}
        onChange={(event) => setFormData((prev) => ({ ...prev, phone: event.target.value }))}
        placeholder="Phone"
        className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-500 transition focus:ring"
      />
      <select
        value={formData.category}
        onChange={(event) =>
          setFormData((prev) => ({ ...prev, category: event.target.value as ContactCategory }))
        }
        className="rounded-md border border-slate-300 px-3 py-2 text-sm outline-none ring-blue-500 transition focus:ring"
      >
        <option value="Friend">Friend</option>
        <option value="Work">Work</option>
        <option value="Family">Family</option>
      </select>

      <button
        type="submit"
        className="sm:col-span-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700"
      >
        Add Contact
      </button>
    </form>
  );
}
